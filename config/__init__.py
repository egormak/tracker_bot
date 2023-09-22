import yaml

# Import config.yaml file
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
print("Load Config")