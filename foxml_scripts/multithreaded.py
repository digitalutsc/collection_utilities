#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import sys
from colorama import Fore
import zipfile
from rich.progress import track
import os
import re
import subprocess
import uuid
from io import BytesIO
import tempfile
import csv
from xml.dom import minidom
import concurrent.futures
from rich.progress import Progress





FOXML_NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'foxml': 'info:fedora/fedora-system:def/foxml#',
    'ns2': 'info:fedora/fedora-system:def/audit#',
    'ns4': 'info:fedora/fedora-system:def/relations-external#',
    'ns5': 'info:fedora/fedora-system:def/model#',
    'ns6': 'http://islandora.ca/ontology/relsext#',
    'ns7': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
    'ns9': 'urn:oasis:names:tc:xacml:1.0:policy',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}
bag_name_and_new_foxml = []


def print_help() -> None:
    pass

def parse_arguments(arguments: list[str]) -> str:
    """ Parse the <arguments> passed to this script via the command line and return the path of the input directory."""
    # Display the help message if the user requests it
    if '--help' in arguments or '-h' in arguments:
        print_help()
        sys.exit(0)

    if len(arguments) != 2:
        print(Fore.RED, "Invalid number of arguments. Expected 1, but got", len(arguments) - 1, Fore.RESET)
        sys.exit(127)
    else:
        return arguments[1]
    
def create_uniquely_named_directory() -> str:
    """ Creates a uniquely-named directory in the system's temp directory and returns its path. """

    # Get the system's temporary directory location
    temp_dir = tempfile.gettempdir()

    # Generate a unique directory name using UUID
    unique_name = "dir_" + str(uuid.uuid4())

    # Combine the temp_dir and unique_name to get the full path of the new directory
    new_directory_path = os.path.join(temp_dir, unique_name)

    # Create the directory if it doesn't exist
    os.makedirs(new_directory_path, exist_ok=True)

    return new_directory_path
    
def format_drush_command_from_atomzip(zip_path: str) -> str:
    """Return 'drush @dsu --user=1 create-islandora-bag object COLLECTION:PID', where <zip_path> is of the form .../COLLECTION_PID_foxml_atomzip.zip"""

    # Extract the COLLECTIONNAME:PID from the zip_path
    zip_filename = os.path.basename(zip_path).replace('_foxml_atomzip.zip', '')
    
    # Find the last index of '_' in the filename
    last_underscore_index = zip_filename.rfind('_')
    
    # Split the filename into COLLECTION and PID parts using the last underscore index
    collection_name = zip_filename[:last_underscore_index]
    pid = zip_filename[last_underscore_index + 1:]

    # Combine COLLECTION and PID with ':' and return the formatted drush command
    return f"drush @dsu --user=1 create-islandora-bag object {collection_name}:{pid}"


def extract_bag_path_from_drush_command_stdout(stdout_bytes: bytes) -> str:
    """Given <stdout_bytes> from the 'drush @dsu --user=1 create-islandora-bag object COLLECTION:PID' command, return the path of the newly created ZIP file."""
    # Decode the stdout bytes to a string
    stdout = stdout_bytes.decode('utf-8')
    
    # Define a regular expression pattern to match the bag path up to ".zip"
    pattern = r"Bag created and saved at ([^\n]+?\.zip)"
    
    # Use re.findall() to find all occurrences of the pattern in the stdout
    matches = re.findall(pattern, stdout)
    
    if matches:
        # Extract the path from the first matched group (up to ".zip")
        bag_path = matches[0]
        return bag_path.strip()  # Remove any leading/trailing whitespace from the path
    else:
        return None  # Return None if no path is found in the stdout
    

def get_XML_tree_zip_file(target_filename: str, zip_ref: zipfile.ZipFile) -> ET.Element:
    """ Searches for a specific filename inside a ZipFile object (including nested zip files) and returns a read stream to the first matching file found. """
    for name in zip_ref.namelist():
        if re.search(r'\.zip$', name) is not None:
            # We have a nested zip within the main zip
            with zip_ref.open(name) as nested_zip_file:
                # Read the whole nested zip entry into memory
                zfiledata = BytesIO(nested_zip_file.read())
                with zipfile.ZipFile(zfiledata, 'r') as nested_zip_ref:
                    nested_result = get_XML_tree_zip_file(
                        target_filename,
                        nested_zip_ref
                    )
                if nested_result:
                    return nested_result
        else:
            filename = os.path.basename(name)
            if target_filename in filename:
                # Read the content of the XML file from the ZipExtFile object
                xml_content = zip_ref.read(name)
                # Convert the bytes content to a string and parse it with ElementTree
                try:
                    return ET.fromstring(xml_content.decode('utf-8'))
                except ET.ParseError as e:
                    error_message = str(e)
                    if 'junk after document element' in error_message:
                        return ET.fromstring(re.sub(r"(<\?xml[^>]+\?>)", r"\1<root>", xml_content.decode('utf-8')) + "</root>")
                    else:
                        raise e
    return None
      

def is_foxml_managed(foxml_root: ET.Element) -> bool:
    """ Given the <foxml_root> of a foxml.xml file, return True if the MODS are managed, False otherwise. """

    # Find the <foxml:datastream> element with ID="MODS" using the namespace prefix
    datastream_element = foxml_root.find(".//foxml:datastream[@ID='MODS']", FOXML_NAMESPACES)
    if datastream_element is not None:
        # Get the value of the CONTROL_GROUP attribute
        control_group = datastream_element.get("CONTROL_GROUP")
        # Check if the value is "M"
        return control_group == "M"
    return False

def managed_to_inline(foxml_root: ET.Element, bag_archive: zipfile.ZipFile) -> None:
    """ Given a <foxml_root> with managed MODS (where the MODS files are in <bag_archive>), mutate is so it becomes inline MODS."""

    # Find the <foxml:datastream> element with ID="MODS"
    datastream = foxml_root.find(".//foxml:datastream[@ID='MODS']", namespaces=FOXML_NAMESPACES)
    # Update the CONTROL_GROUP attribute value to "X", as MODS are now inline effective immediatly.
    datastream.set("CONTROL_GROUP", "X")
    # Find all the <foxml:datastreamVersion> elements within the <foxml:datastream>
    datastream_version_elements = datastream.findall(".//foxml:datastreamVersion", FOXML_NAMESPACES)
    # Loop over every datastreamVersion element and make them inline
    for datastream_version_element in datastream_version_elements:
        if datastream_version_element:
            # Remove the currentLocation element as there will no longer be a MODS file
            content_location_element = datastream_version_element.find(".//foxml:contentLocation", namespaces=FOXML_NAMESPACES)
            if content_location_element:
                datastream_version_element.remove(content_location_element)
            mods_root = get_XML_tree_zip_file(datastream_version_element.get('ID'), bag_archive)
            for element in mods_root.iter():
                # Remove the namespace prefix from the tag if present
                if '}' in element.tag:
                    element.tag = element.tag.split('}', 1)[1]

                # Remove the ns3 prefix from attributes if present
                for key, value in element.attrib.items():
                    if '}' in value:
                        element.attrib[key] = value.split('}', 1)[1]
            # Wrap the additional XML content in <foxml:xmlContent>
            xml_content_element = ET.Element("{info:fedora/fedora-system:def/foxml#}xmlContent")
            # Define the <mods> element with its namespaces
            mods_element = ET.Element(
                "mods",
                attrib={
                    "xmlns": "http://www.loc.gov/mods/v3",
                    "xmlns:mods": "http://www.loc.gov/mods/v3",
                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "xmlns:xlink": "http://www.w3.org/1999/xlink",
                },
            )
            xml_content_element.append(mods_element)

            mods_element.extend(mods_root)

            # Insert the <foxml:xmlContent> element to the datastream_version
            datastream_version_element.append(xml_content_element)

def get_bag_name_from_atomzip(atomzip_path: str) -> str:
    """ Given an <atomzip_path>, return the name of the bag contained in the atomzip name. """
    return os.path.basename(atomzip_path).replace('_foxml_atomzip.zip', '')

# Parse command line arguments and extract the path of the input zip file
input_dir = parse_arguments(sys.argv)

# Create the directory which will store the FOXML files
return_directory = create_uniquely_named_directory()

# Register the namespaces to preserve the original prefixes
ET.register_namespace("foxml", "info:fedora/fedora-system:def/foxml#")
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
ET._namespace_map["info:fedora/fedora-system:def/foxml#"] = "foxml"

def process_container_zip(input_zip: str) -> None:
    if not os.path.basename(input_zip).endswith('.zip'):
        return
    output_directory = f'{return_directory}/{os.path.basename(input_zip).replace(".zip", "")}'
    os.makedirs(output_directory)
    found_first_atomzip = False
    with zipfile.ZipFile(f'{input_dir}/{input_zip}', 'r') as zip_archive:
        for name in zip_archive.namelist():
            # Check if the file matches the desired pattern (inside data directory and ends with _foxml_atomzip.zip)
            if 'data/' in name and name.endswith('_foxml_atomzip.zip'):
                bag_name = get_bag_name_from_atomzip(name)

                # We do not need to run any Drush command for the first atomzip to get the FOXML, as the foxml file is already in the given ZIP
                if not found_first_atomzip and name not in input_zip:
                    found_first_atomzip = True
                    foxml_root = get_XML_tree_zip_file('foxml.xml', zip_archive)
                else:
                    # Execute the Drush command to add a FOXML file to this ZIP file
                    result = subprocess.run(format_drush_command_from_atomzip(name), shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    # Extract the path of the newly created ZIP file (by the Drush command), which will contain the FOXML file in it
                    bag_path = extract_bag_path_from_drush_command_stdout(result.stdout)
                    if not bag_path:
                        print(Fore.RED, f"Drush command failed for {name}. Skipping this bag.", Fore.RESET)
                        continue
                    with zipfile.ZipFile(bag_path, 'r') as bag_archive:
                        foxml_root = get_XML_tree_zip_file('foxml.xml', bag_archive)

                if is_foxml_managed(foxml_root):
                    print(Fore.GREEN, f'{bag_name} contains a managed FOXML file. Making it inline.', Fore.RESET)
                    try:
                        managed_to_inline(foxml_root, zip_archive)
                    except Exception as e:
                        print(Fore.RED, f'There was an error with converting {bag_name}\'s FOXML to inline; conversion will be skipped: {str(e)}', Fore.RESET)
                else:
                    print(Fore.GREEN, f'{bag_name} contains an inline FOXML file. This will simply beautify it.', Fore.RESET)

                # Ensure that the original namespace prefix is used in the output file
                # xml_string = minidom.parseString(ET.tostring(foxml_root)).toprettyxml(indent="   ")
                # with open(converted_foxml_path, 'w') as converted_foxml_file:
                #     converted_foxml_file.write(xml_string)
                # ET.ElementTree(foxml_root).write(converted_foxml_path, encoding="utf-8", xml_declaration=True)
                
                xml_string = ET.tostring(foxml_root).decode()

                # Prepare the xmllint command and arguments
                command = ["xmllint", "--format", "-"]
                try:
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate(input=xml_string, timeout=10)

                    # Check for any errors
                    if process.returncode != 0:
                        print("Error occurred while formatting XML:")
                        print(stderr)
                    else:
                        formatted_xml_string = stdout

                    foxml_save_directory = os.path.join(output_directory, bag_name)
                    os.makedirs(foxml_save_directory)
                    converted_foxml_path = f'{foxml_save_directory}/foxml.xml'

                    # Write the formatted XML string to the file
                    with open(converted_foxml_path, 'w') as converted_foxml_file:
                        converted_foxml_file.write(formatted_xml_string)

                except subprocess.TimeoutExpired:
                    print("Process took too long to execute.")
                except Exception as e:
                    print("An error occurred:", str(e))
                bag_name_and_new_foxml.append([bag_name, converted_foxml_path])



def run(zip_files):
    total = len(zip_files)
    progress = Progress()

    with progress:
        task = progress.add_task("[cyan]Processing...", total=total)

        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [executor.submit(process_container_zip, input_zip) for input_zip in zip_files]

            for future in concurrent.futures.as_completed(futures):
                progress.advance(task)






print(Fore.YELLOW, f"Conversion has started. The output directory is {return_directory}")
print(Fore.YELLOW, f'Please refer to {return_directory}/map.csv for a mapping of bags to their converted FOXML files.', Fore.RESET)

# with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
#     zip_files = [zip_file for zip_file in os.listdir(input_dir) if zip_file.endswith('.zip')]
#     futures = [executor.submit(process_container_zip, input_zip) for input_zip in zip_files]

zip_files = [zip_file for zip_file in os.listdir(input_dir) if zip_file.endswith('.zip')]
run(zip_files)

with open(f'{return_directory}/map.csv', 'w', newline='') as map:
    writer = csv.writer(map)

    # Write the column names to the CSV file
    writer.writerow(['bag_name','converted_foxml_path'])

    # Write the accumulated data to the CSV file in bulk
    writer.writerows(bag_name_and_new_foxml)
                

            

