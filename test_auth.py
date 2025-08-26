import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# Load your credentials from YAML
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

credentials = config['credentials']

hasher = stauth.Hasher()

hashed_credentials = hasher.hash_passwords(credentials)

print(hashed_credentials)
