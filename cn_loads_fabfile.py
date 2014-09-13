


from datetime import datetime, timedelta
import fabric
from fabric.api import *
import os
import paramiko
import re
import socket
import yaml



@task
@runs_once
def cn_loads():
    """Determines the available computing power of all connectable CN machines.

    Prints output to stdout.
    """

    # Change the definition of this list to reflect the available machines
    cn_machines = ['cn'+str(i) for i in xrange(1,25)] # if i not in [0]]

    # Try to connect to all known machines to see which ones respond.
    # If a machine is down for maintenence, or so overloaded that it
    # can't even respond right away, we don't want to query it further.
    with fabric.context_managers.hide("running"):
        connectivity = execute(test_connectivity, hosts=cn_machines)
    for host in connectivity:
        if connectivity[host] == False:
            cn_machines.remove(host)

    # Get CPU load, count, and clock of the machines that did respond
    avg_loads, cpu_counts, cpu_clocks = {}, {}, {}
    with fabric.context_managers.hide("running"):
        avg_loads  = execute(get_avg_load,  hosts=cn_machines)
        #cpu_counts = execute(get_cpu_count, hosts=cn_machines)
        #cpu_clocks = execute(get_cpu_clock, hosts=cn_machines)

    # Read local DB instead of querying remote machines, when possible
    cpu_counts, cpu_clocks = get_cpu_counts_and_clocks(hosts=cn_machines)

    # Calculate available computing power of each machine:
    # (1.0-(avg_load/100.0)) * num_processors * clockrate
    power = {}
    for host in avg_loads:
        power[host] = ((1.0-(avg_loads[host]/100.0))
                       * cpu_counts[host]
                       * cpu_clocks[host])

    for host in sorted(power, key=power.get, reverse=False):
        print("{Host:4s}  |  load: {Load: >4.1f}%  |  cpus: {CPUs: >2d}  @  {Clock: >4.2f} GHz  |  power: {Power: >5.2f}"
              .format(Host = host,
                      Load = avg_loads[host],
                      CPUs = cpu_counts[host],
                      Clock = cpu_clocks[host],
                      Power = power[host]))



@task
@parallel
def test_connectivity(verbose=False):
    """Tests to see if we can SSH to a machine in a reasonable time.

    Returns:
        True if successful
    """

    connectable = None
    time_out = 1  # Number of seconds for timeout
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(env.host, timeout=time_out)
        connectable = True
    except paramiko.AuthenticationException:
        print("Error: On host = {Host}, Authentication problem during connectivity test"
              .format(Host = env.host))
        connectable = False
    except socket.error, e:
        print("Error: On host = {Host}, Communication problem during connectivity test"
              .format(Host = env.host))
        connectable = False
    ssh.close()

    if verbose:
        print("{Host:4} | connectable?: {Connectable}".format(Host=env.host, Connectable=connectable))

    return connectable



def read_db():
    """Reads database with historic values for cpu count and clock

    If file exists, opens it and reads it, parsing as YAML
    If file does not exist or is empty, returns an empty dict
    """

    # Look for database in the same folder as this script
    script_dir = os.path.dirname(os.path.realpath(__file__))
    db_filepath = os.path.join(script_dir, 'cn_loads_database.dat')

    db = None
    if os.path.isfile(db_filepath):
        with open(db_filepath, 'r') as f:
            db = yaml.load(f.read())
            if db == None:
                db = dict()
    else:
        db = dict()

    return db



def write_db(db):
    """Writes database with historic values for cpu count and clock

    If file exists, it will be overwritten
    """

    # Look for database in the same folder as this script
    script_dir = os.path.dirname(os.path.realpath(__file__))
    db_filepath = os.path.join(script_dir, 'cn_loads_database.dat')

    with open(db_filepath, 'w') as f:
        f.write(yaml.dump(db, default_flow_style=False))



def get_cpu_counts_and_clocks(hosts, verbose=False):
    """Determines CPU counts and clocks

    Reads YAML database for historic values
    Builds a list of hosts that need to be queried
      either because they're not in DB, or their value in DB is too old
    Executes get_cpu_count and get_cpu_clock in parallel on those hosts
    Writes new values and update times, if any, to database
    Returns dicts mapping host -> cpu_count and host -> cpu_clock
      like execute(get_cpu_count, hosts) & execute(get_cpu_clock, hosts)
    """

    db = read_db()

    now = datetime.now()
    one_week_delta = timedelta(weeks=1)

    # Determine which hosts need to be updated
    to_update = []
    for host in hosts:
        if host not in db:
            to_update.append(host)
        else:
            last_update = datetime.strptime(db[host]['update_time'], "%Y-%m-%d %H:%M:%S")

            if (now - last_update) > one_week_delta:
                to_update.append(host)

    if verbose:
        print 'Updating hosts:'
        for host in to_update:
            print ' ' + host

    cpu_counts, cpu_clocks = {}, {}
    if to_update:
        with fabric.context_managers.hide("running"):
            cpu_counts = execute(get_cpu_count, hosts=to_update)
            cpu_clocks = execute(get_cpu_clock, hosts=to_update)

    # Add updated information to db
    for host in to_update:
        if host not in db:
            db[host] = {}

        db[host]['cpu_count']   = cpu_counts[host]
        db[host]['cpu_clock']   = cpu_clocks[host]
        db[host]['update_time'] = now.strftime("%Y-%m-%d %H:%M:%S")
    write_db(db)

    counts = {host : db[host]['cpu_count'] for host in hosts}
    clocks = {host : db[host]['cpu_clock'] for host in hosts}

    return counts, clocks



@task
@parallel
def get_cpu_count(verbose=False):
    """Gets a count of the CPUs on the remote machine.

    First tries to get a historical value from database, so we don't generate
    unnecessary network traffic. If that value is too old, connect to the
    machine and determine CPU count from the file /proc/cpuinfo

    Returns:
        CPU count (a positive integer) if successful
        None otherwise
    """

    output = run("cat /proc/cpuinfo | grep processor | tail -1", quiet=True)

    regex = re.compile(
    """
    .*processor  # any chars before "processor"
    \s*:\s*      # any amount of whitespace, colon, any amount of whitespace
    (\d*)        # any digits
    \s*          # any amount of whitespace
    """, re.VERBOSE)

    matches = regex.findall(output)

    num_cpus = None
    if (len(matches) == 1):
        num_cpus = int(matches[0])+1 # Correct for zero-based cpu numbering
    else:
        print("Error: On host = {Host}, unable to match cpu count in string\n{Output}"
              .format(Host = env.host, Output=output))

    if verbose:
        print("{Host:4} | CPU count: {count}".format(Host=env.host, count=num_cpus))

    return num_cpus



@task
@parallel
def get_cpu_clock(verbose=False):
    """Gets CPU clock on the remote machine.

    First looks for max CPU clock from the file
    /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq

    Or, failing that, get current clock from
    /proc/cpuinfo

    The first file seems to only exist if the powersaving module is configured
    a certain way on the host. The second file seems to always exist, but if
    powersaving is in use on the host and there is little load, it may report
    a clock that is substantially less than the max.

    Returns:
        CPU clock in GHz (a positive float) if successful
        None otherwise
    """

    fn = '/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq'
    output = run("cat " + fn, quiet=True)
    # This file apparently only exists if the kernel's power saving module is
    # configured a certain way. I have so far only seen it on cn10 and cn11.
    # It looks like the units are kHz.

    clock_in_GHz = None

    try:
        clock_in_kHz = int(output)
        clock_in_GHz = float(clock_in_kHz) / (10**6)
        return clock_in_GHz
    except ValueError:
        if verbose:
            print("Error: On host = {Host}, unable to get cpu clock in string\n{Output}"
                  .format(Host=env.host, Output=output))

    # The cpuinfo_max_freq file approach didn't work, so get current clock
    # from /proc/cpuinfo
    output = run("cat /proc/cpuinfo | grep MHz | uniq", quiet=True)

    regex = re.compile(
    """
    .*cpu\sMHz  # any chars before "cpu MHz"
    \s*:\s*     # any amount of whitespace, colon, any amount of whitespace
    (\d*.?\d*)  # any digits, <= 1 period, any digits (i.e. any positive float)
    \s*         # any amount of whitespace
    """, re.VERBOSE)

    matches = regex.findall(output)

    if (len(matches) == 1):
        clock_in_GHz = float(matches[0]) / (10**3)   # MHz to GHz
    else:
        print("Error: On host = {Host}, unable to determine cpu frequency in string\n{Output}"
              .format(Host = env.host, Output = output))

    if verbose:
        print("{Host:4} | CPU clock: {Clock:4.2f} GHz".format(Host=env.host, Clock=clock_in_GHz))

    return clock_in_GHz



@task
@parallel
def get_avg_load(verbose=False):
    """Gets the average CPU load on a remote machine.

    Uses
      Returns a number from 0.0-100.0 if successful
      Returns None otherwise
    """
    output = run("top -d0.5 -n4 | grep Cpu", quiet=True)

    # Strip formatting control characters (top output can have a lot of these)
    output = (output.replace('\x1b(B','')
                    .replace('\x1b[m','')
                    .replace('\x1b[K','')
                    .replace('\x1b[39;49m',''))

    output = output.splitlines()

    loads = []
    for i in xrange(len(output)):
        # Top output tends to look like
        #   Cpu(s):  2.9%us,  0.0%sy,  0.0%ni, ...     OR
        #   Cpu(s):  2.9% us,  0.0% sy,  0.0% ni, ...  OR
        #   %Cpu(s): 2.9 us,  0.0 sy,  0.0 ni, ...
        # We use a regex to match the floating point value for percentage load
        regex = re.compile(
        """
        .*Cpu\(s\):  # any chars before "Cpu(s):"
        \s*          # any amount of whitespace
        (\d*.?\d*)   # any digits, <= 1 period, any digits (i.e. any positive float)
        \s*          # any amount of whitespace
        %?           # <= 1 percent symbol (some versions of top just have one "%" on this line, before "Cpu(s)"
        \s*          # any amount of whitespace
        us           # total system load appears to be marked "us"
        """, re.VERBOSE)

        matches = regex.findall(output[i])
        #print(repr(output[i]))
        if (len(matches) == 1):
            load = float(matches[0])
            loads.append(load)
        else:
            print("Error: On host = {Host}, unable to match total cpu load in string\n{Output}"
                  .format(Host = env.host, Output = output[i]))

    # Throw out the first record of CPU load because it always seems to spike
    # briefly after the command is issued.
    loads = loads[1:]
    avg_load = None
    if len(loads) != 0:
        avg_load = sum(loads)/float(len(loads))
    else:
        print("Error: On host = {Host}, len(loads) == 0"
              .format(Host = env.host))

    if (verbose):
        print("{Host:4} | Average load: {Load:3.2f}%".format(Host=env.host, Load=avg_load))

    return avg_load



