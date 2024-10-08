import xml.etree.ElementTree as ET
from pprint import pprint
import os
import sys
import re
import argparse
from io import StringIO

defines = {}
current_master_data = None
current_group_data = None
current_global_data = None  # Para manejar <global>

# Clase para almacenar información de muestras
class Sample:
    def __init__(self):
        self.sample_path = None
        self.key = None
        self.control = {}
        self.filechannel = 1
        self.channel = None
        self.instrument = None
        self.hivel = None
        self.seq_position = 1

# Función para manejar la carga de un archivo SFZ
def parse_sfz(sfz_path, base_dir):
    global current_master_data
    global current_group_data
    global current_global_data

    samples = []
    default_path = base_dir
    current_section = ''

    with open(sfz_path, 'r') as sfz_file:
        lines = sfz_file.readlines()
        sample_data = Sample()

        for line in lines:
            line = line.strip()

            print (line)
            # Manejar default_path
            if line.startswith("default_path="):
                default_path = os.path.join(base_dir, line.split('=')[1].strip())
                continue

            # Manejar #define
            if line.startswith("#define"):
                parts = line.split()
                if len(parts) == 3:
                    define_key = parts[1]
                    define_value = parts[2]
                    defines[define_key] = define_value
                continue

            # Reemplazar variables definidas en las líneas posteriores
            for define_key, define_value in defines.items():
                line = line.replace(define_key, define_value)

            # Manejar incluye
            if line.startswith("#include"):
                include_path = line.split('"')[1]
                include_full_path = os.path.join(base_dir, include_path)
                if os.path.exists(include_full_path):
                    print(f"Incluyendo {include_full_path}")
                    #samples.extend(parse_sfz(include_full_path, os.path.dirname(include_full_path)))
                    samples.extend(parse_sfz(include_full_path, base_dir))
                else:
                    print(f"El fichero {include_full_path} No existe")
                    sys.exit()
                continue

            # Manejar <master>
            if line.startswith("<master>"):
                current_master_data = {}  # Reiniciar los datos del master
                current_section = 'master'
                continue
            # Manejar <group>
            elif line.startswith("<group>"):
                current_group_data = current_master_data.copy()  # Copia los datos del master al grupo
                current_section = 'group'
                continue
            # Manejar <global>
            elif line.startswith("<global>"):
                current_global_data = {}  # Reiniciar los datos globales
                current_section = 'global'
                continue
            # Manejar <control>
            elif line.startswith("<control>"):
                sample_data.control = {}  # Reiniciar datos de control
                current_section = 'control'
                continue
            # Manejar <region>
            elif line.startswith("<region>"):
                sample_data = Sample()  # Crear nueva instancia para la región
                current_section = 'region'
                continue

            if line.startswith("sample="):
                if (current_section == 'region'):
                    sample_path = line.split('=')[1].strip()
                    #sample_data.sample_path = os.path.join(default_path, sample_path) if not os.path.isabs(sample_path) else sample_path
                    sample_data.sample_path = sample_path
                    continue
                else: 
                    print("warning: Error, un sample= deberia estar dentro de una region")
                    #sys.exit()
                    continue
            
            if line.startswith("pitch_keycenter="):
                if (current_section == 'region'):
                    sample_data.midi_note = int(line.split('=')[1].strip())
                    continue
                else:
                    print("Error, un pitch_keycenter= deberia estar dentro de una region")
                    sys.exit()

            if '=' in line and current_section=='master':
                # Procesar múltiples asignaciones en una línea
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        current_master_data[key.strip()] = value.strip()
                continue
            elif '=' in line and current_section=='group':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        current_group_data[key.strip()] = value.strip()
                continue
            elif '=' in line and current_section=='global':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        current_global_data[key.strip()] = value.strip()
                continue
            elif '=' in line and current_section=='control':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        sample_data.control[key.strip()] = value.strip()
                continue
            elif '=' in line and current_section=='region':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        key = key.strip()
                        value = value.strip()
                        if hasattr(sample_data, key):
                            setattr(sample_data, key, value)

            #if len(line) == 0 and sample_data.sample_path and sample_data.midi_note is not None:  # Fin de la región
            #if len(line) == 0 and sample_data.sample_path is not None and sample_data.midi_note is not None:  # Fin de la región
            if len(line) == 0 and sample_data.sample_path is not None:  # Fin de la región
                sample_data.__dict__.update({k: v for k, v in current_master_data.items() if hasattr(sample_data, k)})  # Copiar datos del grupo
                sample_data.__dict__.update({k: v for k, v in current_global_data.items() if hasattr(sample_data, k)})  # Copiar datos del grupo
                sample_data.__dict__.update({k: v for k, v in current_group_data.items() if hasattr(sample_data, k)})  # Copiar datos del grupo
                elementos = sample_data.sample_path.split('/')
                sample_data.channel=elementos[2]
                string = sample_data.sample_path.split('_')
                if (elementos[3] in string):
                    pos = string.index(elementos[3])
                    sample_data.instrument=elementos[3]+' '+string[pos+1]
                else:
                    sample_data.instrument=elementos[3]
                samples.append(sample_data)
                #pprint (current_master_data)
                #pprint (current_global_data)
                #pprint (current_group_data)
                pprint (vars(sample_data))
                #print (base_dir)
                #sys.exit()


    return samples

# Función para crear el archivo XML de DrumGizmo
def create_drumgizmo_midimap(samples, output_xml_path):
    # Crear el árbol XML
    kit = ET.Element("midimap")
    maps = []

    for idx, sample in enumerate(samples):

        if not any(new_map == (sample.key, sample.instrument) for new_map in maps):
            maps.append((sample.key, sample.instrument))

            map = ET.SubElement(kit, "map")
            map.set('note', sample.key)
            map.set('instr', sample.instrument)
    
    # Crear el árbol XML
    tree = ET.ElementTree(kit)
    ET.indent(tree, f" ")

    output = StringIO()

    # Escribir el XML al archivo de salida
    tree.write(output_xml_path+'_midimap', encoding='utf-8', xml_declaration=True)
    print(f"XML de DrumGizmo creado: {output_xml_path}_midimap")

# Función para crear el archivo XML de DrumGizmo
def create_drumgizmo_xml(samples, output_xml_path):
    # Crear el árbol XML
    kit = ET.Element("drumkit")
    metadata = ET.SubElement(kit, "metadata")
    channels = ET.SubElement(kit, "channels")
    instruments = ET.SubElement(kit, "instruments")

    samples_channel = {}
    
    for idx, sample in enumerate(samples):
        if sample.channel not in samples_channel:
            samples_channel[sample.channel] = []
            channel = ET.SubElement(channels, 'channel')
            channel.set('name', sample.channel)

    # Crear el árbol XML
    tree = ET.ElementTree(kit)
    ET.indent(tree, f" ")

    output = StringIO()

    # Escribir el XML al archivo de salida
    tree.write(output_xml_path, encoding='utf-8', xml_declaration=True)
    print(f"XML de DrumGizmo creado: {output_xml_path}")



parser = argparse.ArgumentParser(description="Params")

parser.add_argument("--input", type=str, help="File Input SFZ", required=True)
parser.add_argument("--output", type=str, help="File Output XML Drumgizmo", required=True)

args = parser.parse_args()

# Ruta del archivo SFZ principal
if not os.path.isfile(args.input):
    print ("El fichero que intentas cargar '{args.input}' no existe\n");
    sys.exit();

# Directorio base donde se encuentran los archivos .sfz y las muestras
base_dir = os.path.dirname(args.input)

# Ruta de salida del archivo XML de DrumGizmo
output_xml_path = args.output

# Leer el archivo SFZ y sus includes
samples = parse_sfz(args.input, base_dir)

# Crear el archivo XML de DrumGizmo
create_drumgizmo_midimap(samples, output_xml_path)

# Crear el archivo XML de DrumGizmo
create_drumgizmo_xml(samples, output_xml_path)
