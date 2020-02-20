import os
import json
import logging
import importlib
import ssl
import asyncio
import aiozmq
import zmq
from jsonrpcserver import method, async_dispatch as dispatch
import json

logging.basicConfig(format="%(asctime)s %(levelname)s:%(module)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

class poolFramework:
    def __init__(self):
        self.config = json.loads(open("config.json","r").read())
        if self.config['ssl_keyfile_path'] != "" and self['config.ssl_certfile_path'] != "":
           self.ssl_context = loadSSL()
        else:
           self.ssl_context = None
        self.coin_modules = {}
        self.coin_configs = []
        self.startup()
    
    def startup(self):

        directory = os.fsencode(self.config['coin_config_dir'])

        # load configs in config directory
        for filename in os.listdir(directory):
            filename = os.fsdecode(filename)
            if filename.endswith(".json"):
                # checks if the path in config contains a / on the end or not
                if self.config['coin_config_dir'].endswith("/"):
                    curr_config = json.loads(open(self.config['coin_config_dir'] + filename,"r").read())
                else:
                    curr_config = json.loads(open(self.config['coin_config_dir'] + "/" + filename,"r").read())
                
                # only load the config if the file name is the same as the coin name and the script file exsists
                if curr_config['coin'] == filename.replace(".json", "") and os.path.isfile(self.config['coin_modules_dir'] + curr_config['coin'] + ".py"):
                    self.coin_configs.append(curr_config)
                    spec = importlib.util.spec_from_file_location(curr_config['coin'], self.config['coin_modules_dir'] + curr_config['coin'] + ".py")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    self.coin_modules[curr_config['coin']] = module

                    log.info("Added coin module '%s' to modules list", curr_config['coin'])
                elif curr_config['coin'] == filename.replace(".json", "") and os.path.isfile(self.config['coin_modules_dir'] + "/" + curr_config['coin'] + ".py"):
                    self.coin_configs.append(curr_config)
                    spec = importlib.util.spec_from_file_location(curr_config['coin'], self.config['coin_modules_dir'] + curr_config['coin'] + ".py")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    self.coin_modules[curr_config['coin']] = module

                    log.info("Added coin module '%s' to modules list", curr_config['coin'])
            else:
                continue

        # check for duplicate ports

        ports = []
        for config in self.coin_configs:
            if config['port'] in ports:
                log.error(str(config['coin']) + " has the same port configured as another coin!")
                quit
            else:
                ports.append(config['port'])

        for config in self.coin_configs:
            log.info("Initialized " + str(config['coin']) + " stratum")
            #main(self.config, config, log, self.ssl_context)
            asyncio.run(self.coin_modules[config['coin']].main(config, self.config))

    def loadSSL(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.options |= (
            ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
        )
        ssl_context.set_ciphers("ECDHE+AESGCM")
        ssl_context.load_cert_chain(certfile=self['config.ssl_cert_path'], keyfile=self['config.ssl_keyfile_path'])
        ssl_context.set_alpn_protocols(["h2"])

#class Stratum:
#    def __init__(self, main_config, config, log, ssl_context):
#        self.main_config = main_config
#        self.config = config
#        self.log = log
#        self.ssl_context = ssl_context
#        self.template = {"error": None, "id": 0, "result": True}
#        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
#        asyncio.get_event_loop().run_until_complete(self.main())

#    @method
#    class mining:
#        async def authorize(self, username, password):
#            return_json = self.template
#            return_json.id = 2
#            return json.dumps(json.dumps(return_json))
class EchoServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))

        print('Send: {!r}'.format(message))
        self.transport.write(data)

        print('Close the client socket')
        self.transport.close()


class StratumServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        log.info('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        log.debug('Data received: {!r}'.format(message))
        
        try:
            json.loads(message)
        except:
            log.info("Invalid data recieved - " + str(message))
        

        print('Send: {!r}'.format(message))
        self.transport.write(data)

        print('Close the client socket')
        self.transport.close()
poolFramework()
