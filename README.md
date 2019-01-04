# cube-ds

This software is intended to be used as a small-satellite data system. The goal was to create something that can be 
easily configured for different missions and data schemas.

## Getting Started

### Project Layout
This project is layed out in such a way that all the code needed for the project to function lives in the `cubeds` folder.
In this folder, there is a `cubeds/cfg` folder that holds configuration files. There is a `cubeds/decoders` folder that holds all the 
decoders for decoding data. The `cubeds/var` folder holds user defined information about telemetry. The `cubeds/test` folder is
intended to hold test data, but is not necessary.  Other folders that may appear in this location are output file folders.
Also in the `cubeds` folder, on the first level, are all the source files for the program. These _shouldn't_ have to be
changed. All configuration can be done using configuration files, var files, and decoder files.


On the same level as the `cubeds` folder, there is also a `tests` folder that holds both data used for unittesting as
well as the unittests themselves, currently in the file `tests/tests.py`.

### Important Files and Folders
The configuration of this software as it is on Github is a sample configuration for the CSIM spacecraft. There are some
main components that need to be changed to get this software to work for a different spacecraft:
1. `cubeds/cfg/example.yml` is the main configuration file to tell the program things such as where to find other 
configuration files, database information, output files, etc
2. `cubeds/var/packet_defs.csv` tells the program information about potential packets that can be found in the data
3. In this configuration, `cubeds/var/packet_defs.csv` points to `cubeds/var/points` as the main root folder for packet
definitions. This folder is where different packets are stored with their telemetry definitions
4. `cubeds/decoders` is the folder that holds all the decoders. The main idea is that a user can create custom decoders
for their data. Generic decoders like decoder_ccsds.py, decoder_ax25.py, decoder_kiss.py, decoder_vcdu.py, etc should 
work for almost any mission as these are standard data protocols. A template is provided in this folder for an easy start
to building a new decoder

### Creating Telemetry Definition Files
Telemetry definition files provide the program with the core information needed to convert a file from raw data to usable
telemetry data. The file that defines all the packets that can be expected is currently `cubeds/var/packet_defs.csv`. 
CSV files were chosen as they are easily interpreted by everyone therefore knowledge about other data formats are not needed
to configure this portion of the project. The location for the afromentioned file can be altered in the
`cubeds/cfg/example.yml` "telemetry" section (below). This is useful if you want to use telemetry files somewhere else in your
local file system.
 
 ```yaml
telemetry:
  prod:
    packet_definitions: var\packet_defs.csv
    encoding: utf-8-sig
  test:
    packet_definitions: var\packet_defs.csv
    encoding: utf-8-sig
```

The `cubeds/var/packet_defs.csv` is a comma seperated file that should be configured as follows:

| packetName    | apid          | length  | pointsFile             | time_index   |
| ------------- |:-------------:| -------:| ----------------------:| ------------:|
| fsw           | 55            | 512     | var/points/fsw.csv     | tai_seconds  |
| payload       | 56            | 300     | var/points/payload.csv | payload_time |


The `packetName` field defines what the packet is named. This won't affect how the data is processed, but just provides
a way to identify which packet was ingested. It should be unique. 

Missions tend to have multiple different types of packets that they get from their spacecraft. For example, there might
be a shorter state of health packet that just gives necessary information such as voltages and temperatures. But then 
there might also be a larger flight software packet that gives more insight into less critical telemetry. The `apid` 
(Application Identifier) field is the identifier of what mapping of data is going to be in the packet. It should be 
different for every packet type. This value should be defined in your spacecraft documentation. More information about
More information about application identifiers can be found in the [CCSDS space packet protocol documentation](https://public.ccsds.org/Pubs/133x0b1c2.pdf).

The length field is the expected packet length. It doesn't have to be exact, and I would suggest making it slightly
longer than your expected packet. This just tells the program how much data is needed from the start of the packet to
create a full packet.

The `pointsFile` field tells the program where to find the telemetry map for the given packet. It is discussed in more
detail later.

The `time_index` is a rather important field. Data is stored according to a index that will be unique for each packet and
is universal to each packet. One example filed could be CCSDS Time from the CCSDS header. For CSIM, we use the TAI time on
the spacecraft as it is continuous across all packets. This information is used as a primary key in the telemetry database.
The value in the field should be a mnemonic from one of the telemetry points defined in the corresponding `pointsFile`.

For each `pointsFile`, there should be a header field and points defined as follows:

| name          | startByte  | startBit | dtype  | size  | conversion | unit | description       | state      | min | max | endian |
| ------------- |:----------:| --------:| ------:| -----:| ----------:| ----:| -----------------:| ----------:| ---:| ---:| ------:|
| l0_acpt_cnt   | 15         | 0        | dn     | 8     | 0:1          |      | L0 accept counter |            | 0   | 255 | big    |
| tai_seconds   | 55         | 0        | double | 64    | 0:1          | sec  | TAI Seconds       |            |     |     | big    |
| time_valid    | 63         | 0        | dn     | 8     | 0:1          |      | Time Valid        | 1/YES 0/NO | 0   | 1   | big    |

The `name` column is where you define the mnemonic for the telemetry point. This is what will determine how the point will
be differentiated when it is saved. It MUST be unique. This field is required.

The `startByte` is the byte, relative to the beginning of the CCSDS header, at which the telemetry point begins. This
field is required.

The `startBit` is the bit at which the data starts, relative to the startByte. This field is required.

`dtype` can be `dn` for unsigned numbers, `sn` for signed numbers, and `double` for doubles. This field is required.

The size, in *bits* is defined by the `size` field. This field is required.

`conversion` is a polynomial which is used to scale the data. TODO: add polynomial support. If no conversion, enter `0:1`. A polymial conversion of 1.5x^2+3.2x+2.2 would translate to `2.2:3.2:1.5`.

`unit` is the unit of the telemetry. This field can be anything and is not required.

`description` is the description of the telemetry point. It is not required.

`state` is a list of discrete states. States are defined in the following strict format: number/string number/string number/string.
For example: `1/YES 0/NO` or `0/SAFE 1/SUN_POINT 2/FINE_POINT`. This field is not required. Use `dn` as the data format with
this field.

Any data below the value entered in `min` field will be filtered out. This field is not required.

Any data above the value entered in `max` field will be filtered out. This field is not required.

The endianess of the data can be specified in the `endian` field. Not required, will default to "big." Other option
for endianess is "little."

A points file should be specified for each packet, then linked to the `packet_defs.csv` file.

### Creating Custom Decoders
You may need to create (or edit) a decoder when you data does not match the format of data for which these decoders were
built. Each decoder must has its own file in the `cubeds/decoders` folder. The files should follow the structure laid
out in the `cubeds/decoders/template.py` file. A decoder is simply a class that inherits properties from the `Decoder` 
class in `cubeds/decoders/base.py`. For each decoder, the `decode` method is run as the "main." The data passed to the
decoder will be in the instance variable `self.in_data`. Once the data processing has finished for the decoder, put the 
output data into the instance variable `self.out_data`. This allows the main driver to easily pass in and extract out data
from each custom decoder.

In order to make the package see the decoder, you must add it to the `cubeds/decoders/__init__.py` file, similarly to
how the other ones have been added.

Now, you will have to go into your configuration yaml file to add the decoder into the `decoders` section. You will want
to add it to both the `prod` (production) and `test` sections within the `decoders` section. Below is an example of what
an entry looks like for a basic KISS decoder:

```yaml
decoder_stitch_ccsds:
      regex:
      - .*\.kss
      - .*raw_record.*
      priority: 5
```

The `regex` field tells the decoder to what filenames it shall be applied. You can add as many rows as you'd like.

The `priority` field tells the decoder where in order it shall fall with other decoders. For example, a decoder with
a priority of 4 would be run before this decoder, and a decoder with a priority 6 would be run after it. Be careful
to not have two decoders with the same priority that will act on the same files. This could cause you some confusion.

