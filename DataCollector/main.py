import argparse
# from networkCommunication import network
# from serialCommunication import serial

# Constant variables
CFGFILE = "config.cfg"
AVAILABLEMODES = ["network", "serial"]
# AVAILABLEFUNCTIONS: list = [network, serial]

# Data storage
data = {}


# Checks if the configuration file defines the given element
# with the either given or not given choices
def cfgDefines(element, choices = [], cfg=CFGFILE):
    try:
        with open(cfg, "r") as f:
            for line in f.readlines():
                (key, value) = line.strip().split("=")
                if(key == element):
                    if value in choices:
                        return True
                    if choices == [] and value != "":
                        return True
    except: 
        pass         
    return False


def main():
    # PUT DATA INTO CONFIG FILE #

    # Create parser with arguments
    parser = argparse.ArgumentParser(
        description="Puts data from production line to a file"
    )
    parser.add_argument(
        "-f", "--filename",
        required=not cfgDefines("filename")
    )
    parser.add_argument(
        "-m", "--mode",
        choices=AVAILABLEMODES,
        required=not cfgDefines("mode", AVAILABLEMODES)
    )
    parser.add_argument(
        "-k", "--apikey",
        required=not cfgDefines("apikey")
    )

    # If the config file exists then read its data to the data dictionary
    try:
        with open(CFGFILE, "r") as f:
            fileContent = f.readlines()
            for row in fileContent:
                currentElement = row.split("=")
                if (len(currentElement) == 2):
                    data[currentElement[0]] = currentElement[1].strip()
    # If it doesn't exist then create the file
    except:
        with open(CFGFILE, "x"):
            pass

    # Parse the arguments to a dictionary
    args = parser.parse_args()
    argsDict = vars(args)

    # Update the data dictionary with the given arguments
    for k, v in argsDict.items():
        if v is not None:
            data[k] = v

    # Also update the file with the given arguments
    with open(CFGFILE, "w") as f:
        for k, v in data.items():
            f.write(f"{k}={v}\n")

##if __name__ == "__main__":
main()
print("cucc")
