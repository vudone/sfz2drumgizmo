import xml.etree.ElementTree as ET
import os
import sys
import re

# Clase para almacenar información de muestras
class Sample:
    def __init__(self):
        self.sample_path = ""
        self.midi_note = None
        self.loop_mode = None
        self.off_mode = None
        self.control = {}

# Función para manejar la carga de un archivo SFZ
def parse_sfz(sfz_path, base_dir):
    samples = []
    defines = {}
    current_master_data = {}
    current_group_data = {}
    current_global_data = {}  # Para manejar <global>
    default_path = base_dir
    current_section = ''

    with open(sfz_path, 'r') as sfz_file:
        lines = sfz_file.readlines()
        sample_data = Sample()

        for line in lines:
            line = line.strip()

            print ("section: "+current_section)
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
                line = re.sub(rf"\${define_key}", define_value, line)

            # Manejar incluye
            if line.startswith("#include"):
                include_path = line.split('"')[1]
                include_full_path = os.path.join(base_dir, include_path)
                include_full_path = include_path
                if os.path.exists(include_full_path):
                    print(f"Incluyendo {include_full_path}")
                    samples.extend(parse_sfz(include_full_path, os.path.dirname(include_full_path)))
                continue

            # Manejar <master>
            if line.startswith("<master>"):
                current_master_data = {}  # Reiniciar los datos del master
                current_section = 'master'
                continue
            elif '=' in line and current_master_data is not None and current_section=='master':
                # Procesar múltiples asignaciones en una línea
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        current_master_data[key.strip()] = value.strip()
                continue
           
            # Manejar <group>
            if line.startswith("<group>"):
                current_group_data = current_master_data.copy()  # Copia los datos del master al grupo
                current_section = 'group'
                continue
            elif '=' in line and current_group_data is not None and current_section=='group':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        current_group_data[key.strip()] = value.strip()
                continue

            # Manejar <global>
            if line.startswith("<global>"):
                current_global_data = {}  # Reiniciar los datos globales
                current_section = 'global'
                continue
            elif '=' in line and current_global_data is not None and current_section=='global':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        current_global_data[key.strip()] = value.strip()
                continue

            # Manejar <control>
            if line.startswith("<control>"):
                sample_data.control = {}  # Reiniciar datos de control
                current_section = 'control'
                continue
            elif '=' in line and sample_data.control is not None and current_section=='control':
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        sample_data.control[key.strip()] = value.strip()
                continue
    
            # Manejar <region>
            if line.startswith("<region>"):
                sample_data = Sample()  # Crear nueva instancia para la región
                sample_data.__dict__.update(current_group_data)  # Copiar datos del grupo
                current_section = 'region'
                continue
            elif line.startswith("sample="):
                sample_path = line.split('=')[1].strip()
                sample_data.sample_path = os.path.join(default_path, sample_path) if not os.path.isabs(sample_path) else sample_path
            elif line.startswith("pitch_keycenter="):
                sample_data.midi_note = int(line.split('=')[1].strip())
            elif len(line) == 0 and sample_data.sample_path and sample_data.midi_note is not None:  # Fin de la región
                samples.append(sample_data)

            # Manejar configuraciones de la región
            if '=' in line:
                pairs = line.split()
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Dividir solo en el primer '='
                        key = key.strip()
                        value = value.strip()
                        if hasattr(sample_data, key):
                            setattr(sample_data, key, value)

    print (sample_data)
    return samples

# Función para crear el archivo XML de DrumGizmo
def create_drumgizmo_xml(samples, output_xml_path):
    # Crear el árbol XML
    kit = ET.Element("drumkit")
    name = ET.SubElement(kit, "name")
    name.text = "Converted Kit from SFZ"

    for idx, sample in enumerate(samples):
        instrument = ET.SubElement(kit, "instrument")

        # Nombre del instrumento
        instrument_name = ET.SubElement(instrument, "name")
        instrument_name.text = f"instrument_{idx}"

        # Ruta de la muestra (sample)
        filename = ET.SubElement(instrument, "filename")
        filename.text = sample.sample_path

        # Nota MIDI
        midi_note = ET.SubElement(instrument, "midi_note")
        midi_note.text = str(sample.midi_note)

        # Capas de velocidad (esto es opcional, lo básico es un solo sample por nota)
        velocity_layer = ET.SubElement(instrument, "velocity_layer")
        min_vel = ET.SubElement(velocity_layer, "min_velocity")
        max_vel = ET.SubElement(velocity_layer, "max_velocity")
        min_vel.text = "1"
        max_vel.text = "127"

    # Crear el árbol XML
    tree = ET.ElementTree(kit)

    # Escribir el XML al archivo de salida
    tree.write(output_xml_path, encoding='utf-8', xml_declaration=True)
    print(f"XML de DrumGizmo creado: {output_xml_path}")


# Ruta del archivo SFZ principal
if not os.path.isfile(sys.argv[1]):
    print ("El fichero que intentas cargar no existe\n");
    sys.exit();

sfz_path = sys.argv[1]
# Directorio base donde se encuentran los archivos .sfz y las muestras
base_dir = os.path.dirname(sfz_path)
# Ruta de salida del archivo XML de DrumGizmo
output_xml_path = sys.argv[2]

# Leer el archivo SFZ y sus includes
samples = parse_sfz(sfz_path, base_dir)

print (samples)

# Crear el archivo XML de DrumGizmo
create_drumgizmo_xml(samples, output_xml_path)
