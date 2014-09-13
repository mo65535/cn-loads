cn-loads
========

Python Fabric script to check the current load of remote machines


## What is it?

This script gives you some idea of the available computing power
on remote machines. It can be handy if you're in a group where
servers that act as computation nodes for large, long-running
jobs are shared between several people.

The metric used to determine available power is

(1 - load) * number of cores * clock speed

where load is between 0 and 1.

## Using it

To adapt this script to a setup with different machines, you 
will need to modify the line that generates the list of hosts.
You will probaly also want to set up SSH keys (see below).


#### Example run:

I use a shell alias to simplify issuing the command
```bash
alias cnloads fab -f ~/code/fabfiles/cn_loads_fabfile.py cn_loads
```

```
> cnloads

cn1   |  load:  0.0%  |  cpus:  4  @  2.01 GHz  |  power:  8.04
cn17  |  load:  0.1%  |  cpus:  8  @  2.30 GHz  |  power: 18.38
cn19  |  load:  0.1%  |  cpus:  8  @  2.30 GHz  |  power: 18.39
cn7   |  load:  0.1%  |  cpus:  8  @  2.30 GHz  |  power: 18.39
cn20  |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn6   |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn23  |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn18  |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn21  |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn22  |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn5   |  load:  0.0%  |  cpus:  8  @  2.30 GHz  |  power: 18.40
cn3   |  load: 11.9%  |  cpus: 16  @  2.30 GHz  |  power: 32.42
cn16  |  load:  9.7%  |  cpus: 16  @  2.30 GHz  |  power: 33.23
cn12  |  load:  6.4%  |  cpus: 16  @  2.30 GHz  |  power: 34.43
cn9   |  load:  0.5%  |  cpus: 16  @  2.30 GHz  |  power: 36.63
cn13  |  load:  0.1%  |  cpus: 16  @  2.30 GHz  |  power: 36.75
cn15  |  load:  0.0%  |  cpus: 16  @  2.30 GHz  |  power: 36.79
cn2   |  load:  0.0%  |  cpus: 16  @  2.30 GHz  |  power: 36.79
cn8   |  load:  0.0%  |  cpus: 16  @  2.30 GHz  |  power: 36.79
cn24  |  load:  0.0%  |  cpus: 16  @  2.30 GHz  |  power: 36.80
cn14  |  load:  0.0%  |  cpus: 16  @  2.30 GHz  |  power: 36.80
cn4   |  load:  0.0%  |  cpus: 16  @  2.30 GHz  |  power: 36.80
cn10  |  load:  0.1%  |  cpus: 16  @  2.50 GHz  |  power: 39.96
cn11  |  load:  0.1%  |  cpus: 32  @  2.40 GHz  |  power: 76.70

Done.
```

## How does it work?

This script uses the Fabric framework which is designed to simplify 
remote administration of machines by automating the process of SSHing
into those machines and running commands on them.

You'll need to install Fabric. If you have pip, that should be as
simple as


```bash
pip install Fabric
```

That should create a `fab` executable in the `bin/` directory of your
Python install. If that directory is on your path, you're set -- If
not, you'll probably want to make a symlink in a folder that is on
your path (somewhere like `~/bin`) that points to the fab executable.

Then you can use an alias similar to the one above if you want a nice
shortcut for running the script.

### Note:

To save yourself from typing in your password a bunch of times, when
the program runs, you'll also want to set up SSH keys. I think I 
referred to this guide when setting that up for myself: 
http://paulkeck.com/ssh/

Apparently SSH keys can be set up for the case where you use different
usernames and passwords on different machines. In my situation, all
machines are using a shared network drive, and things like username 
and password configuration files are stored there and shared across
the machines. 
