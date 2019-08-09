import click
import pexpect
import re
import os
import csv


@click.command()
@click.argument('switch', nargs=-1)
@click.option('--user', required=True, type=str, help='The username used when connecting to the switch.')
@click.option('--password', prompt=True, hide_input=True, default=lambda: os.environ.get('MAC_REPORT_PASSWORD', ''), required=True, help='The password used when connecting to the switch.')
@click.option('--vlan', required=True, type=int, help='The VLAN to report on.')
@click.option('--ignore-tagged', is_flag=True, help='Ignore ports where the VLAN is tagged.')
@click.option('--ignore-errors', is_flag=True, help='Ignore errors and continue.')
@click.option('--out-file', type=click.File('a+'), help='The file to save MAC addresses in.')
@click.option('-v', '--verbose', count=True, help='Verbosity level. Repeat for higher verbosity.')
def cli(password, switch, user, vlan, ignore_tagged, out_file, verbose, ignore_errors):
    """
    This script will output a list of ports on a given vlan, and the macs seen on that port.
    The --password option may be omitted for a prompt, or set as the MAC_REPORT_PASSWORD environment variable. The SWITCH argument may be repeated.
    """

    if out_file is not None:
        csv_file = csv.writer(out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    with click.progressbar(switch, label='Searching for MAC addresses on VLAN ' + str(vlan)) as switches:
        for switch in switches:
            try:
                if verbose > 0:
                    click.echo('Connecting to ' + switch)
                ssh = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + user + '@' + switch)
                ssh.expect('password:')
                ssh.sendline(password)
                ssh.expect('->')

                # Disable paging
                ssh.sendline('set length 0')
                ssh.expect('->')

                # Save Switch Name
                switchName = ''
                for line in ssh.before.decode().splitlines():
                    if '(' in line:
                        switchName = line.split('(')[0]

                # What ports are interesting?
                if verbose > 0:
                    click.echo('Getting port list for VLAN ' + str(vlan) + '...')
                ssh.sendline('show vlan portinfo vlan ' + str(vlan))
                ssh.expect('->')

                vlanData = ssh.before.decode().splitlines()

                portsWeCareAbout = {}

                for line in vlanData:
                    if re.search(r'^(ge|tg)\.[0-9]*\.[0-9]*', line):
                        if ignore_tagged and 'untagged' not in line:
                            continue
                        port = line.split(' ')[0]
                        portsWeCareAbout[port] = {'label': '', 'macs': []}

                # Do these ports have labels?
                if verbose > 0:
                    click.echo('Getting port labels...')
                ssh.sendline('show port alias')
                ssh.expect('->')
                labelData = ssh.before.decode().splitlines()

                for line in labelData:
                    if re.search(r'(ge|tg)\.[0-9]*\.[0-9]*', line):
                        parts = line.split(maxsplit=2)
                        if len(parts) > 2:
                            port = parts[1]
                            label = parts[2].strip()
                            if port in portsWeCareAbout:
                                portsWeCareAbout[port]['label'] = label

                # What MACs are interesting?
                if verbose > 0:
                    click.echo('Getting MAC addresses on VLAN ' + str(vlan) + '...')
                ssh.sendline('show mac fid ' + str(vlan))
                ssh.expect('->')
                macData = ssh.before.decode().splitlines()

                for line in macData:
                    if re.search(r'(ge|tg)\.[0-9]*\.[0-9]*', line):
                        parts = line.split()
                        mac = parts[0]
                        port = parts[2]

                        if port in portsWeCareAbout:
                            portsWeCareAbout[port]['macs'].append(mac)

                # Dump mac list by port
                for port in portsWeCareAbout.keys():
                    if len(portsWeCareAbout[port]['macs']) > 0:
                        if verbose > 1:
                            click.echo(port + ' ' + portsWeCareAbout[port]['label'])
                        for mac in portsWeCareAbout[port]['macs']:
                            if verbose > 1:
                                click.echo('  ' + mac)
                            if out_file is not None:
                                csv_file.writerow([mac, switch, switchName, port, portsWeCareAbout[port]['label']])
                        if verbose > 1:
                            click.echo()

                # Disconnect, we're done.
                if verbose > 0:
                    click.echo('Disconnecting from ' + switch)
                ssh.sendline('exit')

                # Flush results to file
                out_file.flush()

            except Exception:
                click.echo('Communiations error with ' + switch)
                if not ignore_errors:
                    raise

    if out_file is not None:
        out_file.close()
