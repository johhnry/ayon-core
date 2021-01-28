#!/usr/bin/env bash

# This script will detect Python installation, create venv and install
# all necessary packages from `requirements.txt` needed by Pype to be
# included during application freeze on Unix.


art () {
  cat <<-EOF
 ____________
/\\           \\
\\ \\      ---  \\
 \\ \\     _____/ ______
  \\ \\    \\___/ /\\     \\
   \\ \\____\\    \\ \\_____\\
    \\/____/     \\/_____/   PYPE Club .

EOF
}

# Colors for terminal

RST='\033[0m'             # Text Reset

# Regular Colors
Black='\033[0;30m'        # Black
Red='\033[0;31m'          # Red
Green='\033[0;32m'        # Green
Yellow='\033[0;33m'       # Yellow
Blue='\033[0;34m'         # Blue
Purple='\033[0;35m'       # Purple
Cyan='\033[0;36m'         # Cyan
White='\033[0;37m'        # White

# Bold
BBlack='\033[1;30m'       # Black
BRed='\033[1;31m'         # Red
BGreen='\033[1;32m'       # Green
BYellow='\033[1;33m'      # Yellow
BBlue='\033[1;34m'        # Blue
BPurple='\033[1;35m'      # Purple
BCyan='\033[1;36m'        # Cyan
BWhite='\033[1;37m'       # White

# Bold High Intensity
BIBlack='\033[1;90m'      # Black
BIRed='\033[1;91m'        # Red
BIGreen='\033[1;92m'      # Green
BIYellow='\033[1;93m'     # Yellow
BIBlue='\033[1;94m'       # Blue
BIPurple='\033[1;95m'     # Purple
BICyan='\033[1;96m'       # Cyan
BIWhite='\033[1;97m'      # White


##############################################################################
# Detect required version of python
# Globals:
#   colors
#   PYTHON
# Arguments:
#   None
# Returns:
#   None
###############################################################################
detect_python () {
  echo -e "${BIGreen}>>>${RST} Using Python \c"
  local version_command="import sys;print('{0}.{1}'.format(sys.version_info[0], sys.version_info[1]))"
  local python_version="$(python3 <<< ${version_command})"
  oIFS="$IFS"
  IFS=.
  set -- $python_version
  IFS="$oIFS"
  if [ "$1" -ge "3" ] && [ "$2" -ge "6" ] ; then
    echo -e "${BIWhite}[${RST} ${BIGreen}$1.$2${RST} ${BIWhite}]${RST}"
    PYTHON="python3"
  else
    command -v python3 >/dev/null 2>&1 || { echo -e "${BIRed}FAILED${RST} ${BIYellow} Version [${RST}${BICyan}$1.$2${RST}]${BIYellow} is old and unsupported${RST}"; return 1; }
  fi
}

##############################################################################
# Clean pyc files in specified directory
# Globals:
#   None
# Arguments:
#   Optional path to clean
# Returns:
#   None
###############################################################################
clean_pyc () {
  path=${1:-$pype_root}
  echo -e "${BIGreen}>>>${RST} Cleaning pyc at [ ${BIWhite}$path${RST} ] ... \c"
  find "$path" -regex '^.*\(__pycache__\|\.py[co]\)$' -delete
  echo -e "${BIGreen}DONE${RST}"
}

realpath () {
  echo $(cd $(dirname "$1"); pwd)/$(basename "$1")
}

# Main
art
detect_python || return 1

# Directories
current_dir=$(realpath "$(pwd)")
pype_root=$(realpath "${BASH_SOURCE[0]}")
pushd "$pype_root" > /dev/null

version_command="from pathlib import Path;version = {};pype_root = '$pype_root';with open(pype_root / 'pype' / 'version.py') as fp exec(fp.read(), version);print(version['__version__'])"
# pype_version="$(python3 <<< ${version_command})"

echo -e "${BIYellow}---${RST} Cleaning build directory ..."
rm -rf "$pype_root/build" && mkdir "$pype_root/build" > /dev/null

# echo -e "${BIGreen}>>>${RST} Building Pype [${IGreen} v$pype_version ${RST}]"
echo -e "${BIGreen}>>>${RST} Entering venv ..."
source venv/bin/activate
echo -e "${BIGreen}>>>${RST} Cleaning cache files ..."
clean_pyc
echo -e "${BIGreen}>>>${RST} Building ..."
python "$pype_root/setup.py" build > "$pype_root/build/build.log"
python -B "$pype_root/tools/build_dependencies.py"
echo -e "${BIGreen}>>>${RST} Deactivating venv ..."
deactivate
echo -e "${BICyan}>>>${RST} All done. You will find Pype and build log in \c"
echo -e "${BIWhite}$pype_root/build${RST} directory."
