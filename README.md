# Bible

## Setup for Ubuntu 18.04 LTS
```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.8 python3.8-dev python3-pip vlc
sudo apt upgrade; sudo apt autoremove
python3.8 -m pip install --user pipenv
git clone https://github.com/adamcunnington/Bible.git
cd Bible
pipenv install; pipenv shell
python
```
