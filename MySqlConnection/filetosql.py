"""File to sql: Uploads buffer file contents to database"""

# region imports
import sys
import time
import mysql.connector
import argparse
import re
from os import path
from collections import namedtuple

# endregion

# region settings

# exposed, configurable settings
fields = "address username password dbname filepath logfile"
arg = namedtuple("Argument", "short long req")
args = {
    "filepath": arg("-f", "--filepath", True),
    "username": arg("-u", "--username", True),
    "address": arg("-a", "--address", True),
    "password": arg("-p", "--password", True),
    "logfile": arg("-l", "--logfile", False),
}
Settings = namedtuple("Settings", fields, defaults=[None] * len(fields.split()))

default = Settings(
    address="176.241.29.199",
    dbname="EUPRONET",
)

# endregion

# region absolute paths
dirname = path.dirname(__file__)


def GetFullPath(p, d=dirname):
    if path.isabs(p):
        return p
    else:
        return path.join(d, p)


CFGFILE = GetFullPath("config.cfg")

# endregion

# region 1. Read settings from configuration file

#TODO:  custom exceptions    
cfg = default._asdict()
try:
    with open(CFGFILE, "r", encoding="utf-8") as f:
        pattern = "|".join([f"^{x}$" for x in fields.split()]) # ^field$: exact match
        for line in f.readlines():
            try:
                key, value = [x.strip() for x in line.split("=", 1)]
                if re.match(pattern, key):
                    cfg[key] = value
                else:
                    print(f"Warning: Unexpected setting '{key}'. It will be removed from the config file.")
            except ValueError:
                print(
                    f"Setting '{line.strip()}' is not an assignment. It will be removed from the config file."
                )
except:
    print("Config file doesn't exist or could not be read")

# endregion

# region 2. Ask user for any settings missing
#TODO: arg to revert settings to default from cmd
#TODO: write to cfg even if not all of required settings are specified

parser = argparse.ArgumentParser(description="Uploads buffer file contents to database")


for k, a in args.items():
    # prompt user if config file doesn't define a required value
    req = False
    if a.req:
        c = cfg[k]
        req = c == None or c.strip() == "" #empty or unspecified
    parser.add_argument(a.short, a.long, required=req)

args = vars(parser.parse_args())
for k, v in args.items():
    if v != None and v.strip() != "":
        cfg[k] = v

# endregion

# region 3. Reconstruct config file

def NotEmptyOrNone(value: v):
    return v != None and v.strip() != ""

with open(CFGFILE, "w", encoding="utf-8") as f:
    for k, v in cfg.items():
        if NotEmptyOrNone(v):
            f.write(f"{k} = {v}\n")

cfg = Settings(**cfg)
# endregion

# region 4. Connect to database

try:
    db = mysql.connector.connect(
        host=cfg.address,
        user=cfg.username,
        passwd=cfg.password,
        database=cfg.dbname,
        connect_timeout=3,
    )
except Exception as e:
    print(f"Error: Could not estabilish connection to {cfg.address}: \n {e}")
    sys.exit()

cursor = db.cursor()
# endregion

# region 5. Check if file exists and get country code
filepath = GetFullPath(cfg.filepath)
if not path.isfile(filepath):
    print(f"Could not read file at '{filepath}'")
    db.close()
    sys.exit()

sql = f"SELECT id FROM `countrycodes` WHERE code = '{cfg.username}' LIMIT 1"
cursor.execute(sql)
countrycode = cursor.fetchone()[0]  # TODO: handle if this returns empty
# endregion

# region 6. Upload

# TODO: check if keys given are real column names
# TODO: check if given state values exist and ask to create them if they don't
# TODO: stop adding back unprocessed lines if they were edited at runtime
# TODO: add date if it doesn't exist 
# TODO: correct excused formatting mistakes when writing to history (e.g. ;;;)


def SQLInsert(data, cursor = None, addDate = True, table = "queries"):
    """ Takes in a dictionary of 'columns:values' and
        turns them into an sql insert statement 

        addDate: appends 'date:timestamp' if it doesn't exist yet
        returns the sql query"""

    if addDate and "date" not in data.keys():
        timestamp = time.strftime(r"%Y-%m-%d %H:%M:%S")
        data["date"] = timestamp

    cols = ", ".join(data.keys())
    #!r: uses __repr__ to wrap value in quotes
    vals = ", ".join([f"{p!r}" for p in data.values()])

    return f"INSERT INTO `{table}` ({cols}) VALUES ({vals});"


unprocessed = []

def Upload():
    """ Reads file contents to dictionary
        Sends query
        Updates 'history' and 'unprocessed'
        Returns the  number of queries sent"""
    history = []
    processedLength = 0

    with open(filepath, "r+") as f:
        lines = f.readlines()
        f.truncate(0)
        for l in lines:
            lstr = l.strip()
            if lstr == "" or lstr in [upl.strip() for upl in unprocessed]: continue
            data = {"country": countrycode}
            try:
                for pair in l.split(";"):
                    if(pair.strip() == ""): continue
                    #seperate at the first ':'; remove unneeded whitespace; ignore empty assignments
                    k, v = [x.strip() for x in pair.split(":", 1) if x.strip() != ""]
                    data[k] = v
            except: # Exception as e:
                print(f" Could not parse line {l!r}. It will be left in the buffer file.")  # \n\t {e}")
                unprocessed.append(lstr)
                continue
            
            
            # Send query
            sql = SQLInsert(data)
            print(sql)
            try:
                cursor.execute(sql)
                history.append(l)
            except Exception as e:
                print(f"SQL Error: {e!r}")
                
    with open(filepath, "a") as f:
        f.write("\n".join(unprocessed))

    db.commit()

    if history != [] and cfg.logfile != None:
        with open(GetFullPath(cfg.logfile), "a") as f:
            f.writelines(history)
            f.write("\n")

    return len(history)

# endregion

# region 7. Monitoring

print(
    f"Monitoring {cfg.filepath} [CTRL+C to exit] ..."
)  # TODO animate: Monitoring. .. ...
try:
    while True:
        sent = Upload()
        if sent:
            timestamp = time.strftime(r"%H:%M:%S")
            print(f" {timestamp} - Sent {sent}")
        time.sleep(1)
except KeyboardInterrupt:
    print("Monitoring ended")

# endregion

# region 8. Cleanup

db.close()

# endregion
