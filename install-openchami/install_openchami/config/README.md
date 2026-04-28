# OpenCHAMI Base Configuration

The file `config.yaml` in this directory provides the fully annotated
base configuration of the OpenCHAMI installer. To obtain the contents
of this file complete with annotations for reference, use the

```
install_openchami -b
```

command. To inspect the effect of configuration overlays on the base configuration use

```
install_openchami -c <overlay> [<overlay> ...]
```

To validate an overlaid configuration use

```
install_openchami -v <overlay> [<overlay> ...]
```

__NOTE: While the base configuration is copyrighted and made available
  under the MIT license, displaying that copyright as part of the
  `install_openchami -b` output is cumbersome and unnecessary. Because
  of this a companion `.license` file has been provided that covers
  this base configuration.__
