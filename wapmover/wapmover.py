import click
import pexpect
import os


@click.command()
@click.option('-u', '--user', required=True, type=str, help='The username used when connecting to the switch.')
@click.option('-p', '--password', prompt=True, hide_input=True, default=lambda: os.environ.get('MOVER_PASSWORD', ''), required=True, help='The password used when connecting to the switch.')
@click.option('-f', '--from-file', required=True, type=click.File(mode='r'), help='File to read AP configuration from.')
@click.option('-t', '--to-controller', type=str, help='The controller to apply the configuration to.', metavar='IPADDR')
@click.option('-p', '--wap-prefix', type=str, required=True, help='The prefix of the WAP names to copy.')
@click.option('-w', '--wap-type', multiple=True, type=click.Choice(['AP36xx', 'AP37xx', 'AP38xx']), help='What AP models to copy.')
def cli(from_file, to_controller, wap_prefix, wap_type, user, password):
    """This script copies WAP configuration from one controller to another."""
    config = from_file.readlines()

    indent = 0
    mode = None
    serialToCopy = None
    skipLine = False
    ssh = None

    numAPs = 0

    if to_controller is not None:
        click.echo('Connecting to ' + to_controller)
        ssh = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + user + '@' + to_controller)
        ssh.expect('password:')
        ssh.sendline(password)
        try:
            i = ssh.expect(['#', 'Permission denied'], timeout=120)
            if i > 0:
                click.echo('Incorrect password')
                raise
        except Exception:
            click.echo('ERROR: login failed for ' + to_controller)
            raise

    for line in config:
        # Is this line a comment?
        if line.startswith('#'):
            continue

        skipLine = False

        # What indent level is this line?
        lastIndent = indent
        indent = int((len(line) - len(line.lstrip(' '))) / 4)

        line = line.strip()

        if serialToCopy is not None:
            if indent < lastIndent:
                for x in range(lastIndent - indent):
                    if to_controller is not None:
                        if indent > 0:
                            ssh.sendline('apply')
                            ssh.expect('#', timeout=120)
                        ssh.sendline('exit')
                        ssh.expect('#', timeout=120)

        if indent is 0:
            mode = None
            serialToCopy = None

            if line in 'ap':
                mode = 'ap'

        if mode is not None:
            if mode in 'ap':
                if line.startswith('serial import'):
                    serial = line.split(' ', 3)[2]
                    name = line.split(' ', 3)[3].split('"')[1]
                    model = line.split('"')[2].split(' ')[1]
                    pairmember = line.split('"')[2].split(' ')[3]

                    if pairmember in 'LOCAL':
                        isLocal = True
                    else:
                        isLocal = False

                    if isLocal and name.startswith(wap_prefix):
                        if len(wap_type) > 0:
                            for t in wap_type:
                                t = t.split('x')[0]
                                if model.startswith(t):
                                    serialToCopy = serial
                        else:
                            serialToCopy = serial

                        if serialToCopy is not None:
                            click.echo('Importing ' + model + ' ' + serial + ' as ' + name)
                            numAPs = numAPs + 1
                            if to_controller is not None:
                                ssh.sendline('ap')
                                ssh.expect('#', timeout=120)

                if 'aclist' in line:
                    skipLine = True

                if 'dedicated_scanner' in line:
                    skipLine = True

                if 'wired-mac' in line:
                    skipLine = True

                if 'bindkey' in line:
                    skipLine = True

            if serialToCopy is not None and not skipLine:
                if to_controller is not None:
                    ssh.sendline(line)
                    ssh.expect('#', timeout=120)

    if to_controller is not None:
        click.echo('Imported ' + str(numAPs) + ' APs')
        click.echo('Disconnecting from ' + to_controller)
        ssh.sendline('exit')


def dent(level):
    s = ''
    for x in range(level * 4):
        s = s + ' '

    return s
