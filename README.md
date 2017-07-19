# ttn-icinga
A simple wrapper to enable icinga to check the status of gateways in the things network (https://www.thethingsnetwork.org/)

## Installation
'''
sudo apt install python-pip
sudo pip install python-dateutil
'''

And download the TTNCLI from https://ttnreleases.blob.core.windows.net/release/master/ttnctl-linux-amd64.zip unzip place in /usr/local/bin and make executable

Login to the ttncli
'''
ttnctl user login <accesscode>
'''
with the access code from https://account.thethingsnetwork.org/users/authorize?client_id=ttnctl&redirect_uri=/oauth/callback/ttnctl&response_type=code
