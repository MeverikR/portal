import argparse
import os
import yaml


class Config(object):
    default_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yml')
    if os.path.isfile(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.dev.yml')):
        default_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.dev.yml')

    config = None
    args = ['port', 'host', 'cors']

    @classmethod
    def get_config(cls):
        return cls.config or cls.make_config()

    @classmethod
    def make_config(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', default=cls.default_config_path)
        for arg in cls.args:
            parser.add_argument('--' + arg, required=False)
        args, _ = parser.parse_known_args()
        args = args.__dict__

        with open(args['config'], encoding='utf-8') as file:
            cls.config = yaml.safe_load(file.read())

        for arg in cls.args:
            if args[arg] is not None:
                cls.config[arg] = args[arg]

        return cls.config
