import click
import pexpect
import re
import os
import time


@click.command()
@click.argument('switch', nargs=-1)
@click.option('-u', '--user', required=True, type=str, help='The username used when connecting to the switch.')
@click.option('-p', '--password', prompt=True, hide_input=True, default=lambda: os.environ.get('SWAPPER_PASSWORD', ''), required=True, help='The password used when connecting to the switch.')
@click.option('-f', '--from-vlan', required=True, type=int, help='The VLAN moving from.', multiple=True)
@click.option('-t', '--to-vlan', required=True, type=int, help='The VLAN moving to.')
@click.option('-a', '--tagged-also', is_flag=True, help='Also swap ports where the VLAN is tagged.')
@click.option('-i', '--ignore-errors', is_flag=True, help='Ignore errors and continue.')
@click.option('-c', '--cycle-poe', is_flag=True, help='Power cycle the ports. Does not apply to tagged ports.')
@click.option('-b', '--bounce-ports', is_flag=True, help='Disable/Enable ports. Does not apply to tagged ports.')
@click.option('-v', '--verbose', count=True, help='Verbosity level. Repeat for higher verbosity.')
@click.option('-V', '--verify-vlan', is_flag=True, help='Verify that at VLAN seems okay before making changes.')
@click.option('-r', '--create-vlan', is_flag=True, help='Create the TO VLAN if it doesn\'t exist.')
@click.option('-n', '--create-vlan-name', type=str, help='The name of the TO VLAN.')
def cli(switch, user, password, from_vlan, to_vlan, tagged_also, ignore_errors, cycle_poe, bounce_ports, verbose, verify_vlan, create_vlan, create_vlan_name):
    """
    This script will move ports from one VLAN to another.
    The --password option may be omitted for a prompt, or set as the SWAPPER_PASSWORD environment variable. The SWITCH argument may be repeated. --create-vlan must be used with --verify-vlan.
    """

    for one_switch in switch:
        try:
            if verbose > 0:
                click.echo(click.style('Connecting to ' + one_switch, fg='green'))
            ssh = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + user + '@' + one_switch)
            ssh.expect('password:')
            ssh.sendline(password)
            i = ssh.expect(['->', 'Permission denied'], timeout=120)
            if i > 0:
                click.echo('Incorrect password')
                raise

            # Disable paging
            ssh.sendline('set length 0')
            ssh.expect('->', timeout=120)

            portsWeCareAbout = {}

            # What ports are interesting?
            for f_vlan in from_vlan:
                if verbose > 1:
                    click.echo('Getting port list for VLAN ' + str(f_vlan) + '...')
                ssh.sendline('show vlan portinfo vlan ' + str(f_vlan))
                ssh.expect('->', timeout=120)

                vlanData = ssh.before.decode().splitlines()

                for line in vlanData:
                    if re.search(r'^(ge|tg)\.[0-9]*\.[0-9]*', line):
                        if tagged_also and 'untagged' not in line and 'tagged: ' + str(f_vlan) in line:
                            port = line.split(' ')[0]
                            portsWeCareAbout[port] = {'label': '', 'tagged': True}
                        elif 'untagged: ' + str(f_vlan) in line:
                            port = line.split(' ')[0]
                            portsWeCareAbout[port] = {'label': '', 'tagged': False}

            # Do these ports have labels?
            if verbose > 1:
                click.echo('Getting port labels...')
            ssh.sendline('show port alias')
            ssh.expect('->', timeout=120)
            labelData = ssh.before.decode().splitlines()

            for line in labelData:
                if re.search(r'(ge|tg)\.[0-9]*\.[0-9]*', line):
                    parts = line.split(maxsplit=2)
                    if len(parts) > 2:
                        port = parts[1]
                        label = parts[2].strip()
                        if port in portsWeCareAbout:
                            portsWeCareAbout[port]['label'] = label

            if verify_vlan:
                if verbose > 0:
                    click.echo('Verifying that VLAN ' + str(to_vlan) + ' looks good...')

                # First, verify the VLAN even exists on this switch
                ssh.sendline('show vlan ' + str(to_vlan))
                ssh.expect('->', timeout=120)
                for line in ssh.before.decode().splitlines():
                    if 'does not exist on this device' in line:
                        if create_vlan:
                            ssh.sendline('set vlan create ' + str(to_vlan))
                            ssh.expect('->', timeout=120)
                            time.sleep(30)
                        else:
                            if not ignore_errors and verbose > 0:
                                click.echo(click.style('ERROR: VLAN ' + str(to_vlan) + ' does not exist.', fg='red'))
                            raise

                # Name the VLAN if a name was given
                if create_vlan_name is not None:
                    ssh.sendline('set vlan name ' + str(to_vlan) + ' ' + create_vlan_name)
                    ssh.expect('->', timeout=120)

                # See if we see any mac addresses on this VLAN that might indicate that the other end of uplinks are tagged correctly
                ssh.sendline('show mac fid ' + str(to_vlan))
                ssh.expect('->', timeout=120)
                macData = ssh.before.decode().splitlines()

                foundMac = False

                for line in macData:
                    if re.search(r'(ge|tg)\.[0-9]*\.[0-9]*', line):
                        foundMac = True

                if not foundMac:
                    if not ignore_errors and verbose > 0:
                        click.echo(click.style('ERROR: No MAC addresses found on VLAN ' + str(to_vlan), fg='red'))
                    raise

            # If we made it here, it's time to start swapping out VLANs
            with click.progressbar(portsWeCareAbout, label='Moving ports from VLAN ' + ','.join(map(str, from_vlan)) + ' to ' + str(to_vlan)) as ports:
                for port in ports:
                    if portsWeCareAbout[port]['tagged']:
                        ssh.sendline('set vlan egress ' + str(to_vlan) + ' ' + port + ' tagged')
                        ssh.expect('->', timeout=120)
                    else:
                        if bounce_ports:
                            ssh.sendline('set port disable ' + port)
                            ssh.expect('->', timeout=120)
                        if cycle_poe:
                            ssh.sendline('set port inlinepower ' + port + ' admin off')
                            ssh.expect('->', timeout=120)

                        ssh.sendline('set port vlan ' + port + ' ' + str(to_vlan) + ' modify-egress')
                        ssh.expect('->', timeout=120)

                        if cycle_poe:
                            ssh.sendline('set port inlinepower ' + port + ' admin auto')
                            ssh.expect('->', timeout=120)

                        if bounce_ports:
                            ssh.sendline('set port enable ' + port)
                            ssh.expect('->', timeout=120)

            # Save config
            ssh.sendline('save config')
            ssh.expect('->', timeout=120)

            # Disconnect, we're done.
            if verbose > 1:
                click.echo('Disconnecting from ' + switch)
            ssh.sendline('exit')

        except Exception:
            click.echo('Communiations error with ' + switch)
            if not ignore_errors:
                raise
