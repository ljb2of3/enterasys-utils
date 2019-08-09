# enterasys-utils

This repository contains a small collection of scripts I created recently to assist with a wireless migration project. They are all Click utilities and use setuptools.

https://click.palletsprojects.com/en/7.x/setuptools/

## macreport

This was used to generate a report of every MAC address on a particular VLAN, and what switch and port it was seen on.

```
$ macreport --help
Usage: macreport [OPTIONS] [SWITCH]...

  This script will output a list of ports on a given vlan, and the macs seen
  on that port. The --password option may be omitted for a prompt, or set as
  the MAC_REPORT_PASSWORD environment variable. The SWITCH argument may be
  repeated.

Options:
  --user TEXT          The username used when connecting to the switch.
                       [required]
  --password TEXT      The password used when connecting to the switch.
                       [required]
  --vlan INTEGER       The VLAN to report on.  [required]
  --ignore-tagged      Ignore ports where the VLAN is tagged.
  --ignore-errors      Ignore errors and continue.
  --out-file FILENAME  The file to save MAC addresses in.
  -v, --verbose        Verbosity level. Repeat for higher verbosity.
  --help               Show this message and exit.
```

## vlanswapper

This was used to move switchports from one VLAN to another during the wireless migration. Tested with C5 and D2 series switches.

```
$ vlanswap --help
Usage: vlanswap [OPTIONS] [SWITCH]...

  This script will move ports from one VLAN to another. The --password
  option may be omitted for a prompt, or set as the SWAPPER_PASSWORD
  environment variable. The SWITCH argument may be repeated. --create-vlan
  must be used with --verify-vlan.

Options:
  -u, --user TEXT              The username used when connecting to the
                               switch.  [required]
  -p, --password TEXT          The password used when connecting to the
                               switch.  [required]
  -f, --from-vlan INTEGER      The VLAN moving from.  [required]
  -t, --to-vlan INTEGER        The VLAN moving to.  [required]
  -a, --tagged-also            Also swap ports where the VLAN is tagged.
  -i, --ignore-errors          Ignore errors and continue.
  -c, --cycle-poe              Power cycle the ports. Does not apply to tagged
                               ports.
  -b, --bounce-ports           Disable/Enable ports. Does not apply to tagged
                               ports.
  -v, --verbose                Verbosity level. Repeat for higher verbosity.
  -V, --verify-vlan            Verify that at VLAN seems okay before making
                               changes.
  -r, --create-vlan            Create the TO VLAN if it doesn't exist.
  -n, --create-vlan-name TEXT  The name of the TO VLAN.
  --help                       Show this message and exit.
```

## wapmover

This one reads AP configuration from a file and clones it in to a new ExtremeWireless controller. The config of the source controller is the output of `show run-config`. Note that this doesn't copy WLAN assignments or anything else. Just the AP name, description, and basic radio settings.

```
$ wapmover --help
Usage: wapmover [OPTIONS]

  This script copies WAP configuration from one controller to another.

Options:
  -u, --user TEXT                 The username used when connecting to the
                                  switch.  [required]
  -p, --password TEXT             The password used when connecting to the
                                  switch.  [required]
  -f, --from-file FILENAME        File to read AP configuration from.
                                  [required]
  -t, --to-controller IPADDR      The controller to apply the configuration
                                  to.
  -p, --wap-prefix TEXT           The prefix of the WAP names to copy.
                                  [required]
  -w, --wap-type [AP36xx|AP37xx|AP38xx]
                                  What AP models to copy.
  --help                          Show this message and exit.
  ```

