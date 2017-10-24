
import requests
import re
import os
import re
import sys
import hashlib
import zipfile
import shutil
import datetime



EXCLUDES = ['wp-content']



WP_EXTRACT_LOCATION = '/tmp'
WP_SOURCE_TREE = WP_EXTRACT_LOCATION+'/wordpress/'

if EXCLUDES:
    EXCLUDES = [ exclude.lstrip('/') for exclude in EXCLUDES ]

    
def get_verison(dir_name):
    print('LOG : version -> ',end='')
    try:
        version_regex = r'\$wp_version\s+=\s+\'(\d.\d.\d)\'\;'
        wp_version_file = os.path.join(dir_name,'wp-includes/version.php')
        current_version = re.search(version_regex,open(wp_version_file).read()).group(1)
        print(current_version)
        return current_version
    except Exception as Error:
        print('Failed')
        print(Error)
        sys.exit(1)

        
def get_original_hash(version_number):
    print('LOG : API Call -> ', end='')
    try:        
        api_end = 'https://api.wordpress.org/core/checksums/1.0/?version='+version_number+'&locale=en_US'
        reply = requests.get(api_end)
        page_hash_dict = { location:hash_val for location,hash_val \
                           in reply.json()['checksums'].items() \
                           if not location.startswith(tuple(EXCLUDES)) }
        print('Completed')
        return page_hash_dict
    except Exception as Error:
        print('Failed')
        print(Error)
        sys.exit(1) 

        
        
def get_file_hash(file_name):
    SIZE = 1000000 # 1MB
    hash_object = hashlib.new('md5')
    with open(file_name,'rb') as fh:
        while True:
            data = fh.read(SIZE)
            if not data: 
                break
            hash_object.update(data)
    return hash_object.hexdigest()



def hash_scanner(install_dir , original_hash_dict):
    print('LOG : SCanning :',install_dir,' -> ', end='')
    os.chdir(install_dir) 
    scan_result = { 'missing':[] , 'modified':[] }
    for file_path,hash_value in original_hash_dict.items():
        if os.path.exists(file_path):
            if get_file_hash(file_path) != hash_value:
                scan_result['modified'].append(file_path)
        else:
            scan_result['missing'].append(file_path)
    print('Completed')
    print('LOG : Missing :',len(scan_result['missing']),'Modified :',len(scan_result['modified']))
    return scan_result


def wp_src_download_extract(version):    
    print('LOG : Downloading :','wordpress-'+version,' -> ', end='')
    try:
        wordpress_link = 'https://wordpress.org/wordpress-'+version+'.zip'
        reply = requests.get(wordpress_link,stream=True)
        wp_file_name = WP_EXTRACT_LOCATION+'/wordpress-'+version+'.zip'
        with open(wp_file_name, "wb") as fh:
            for chunk in reply.iter_content(chunk_size=1024):                                       
                if chunk:                                                                           
                    fh.write(chunk)
        print('Successful')
    except Exception as Error:
        print('Failed')    
        print(Error)
        sys.exit(1)
    
    print('LOG : Extracting :', wp_file_name ,' -> ', end='')    
    try:  
        zip_file = zipfile.ZipFile(wp_file_name, 'r')
        zip_file.extractall(WP_EXTRACT_LOCATION)
        zip_file.close()
        print('Successful')
    except Exception as Error:
        print('Failed')    
        print(Error)
        sys.exit(1)

def copy_structure(src_dir,source_files):
    print('LOG : Copying Infected Files -> ', end='')
    os.chdir(install_dir)
    if not os.path.exists(src_dir): 
        os.mkdir(src_dir)
    for file in source_files:
        dir_name = os.path.dirname(file)
        final_dir_path = os.path.normpath(src_dir+'/'+dir_name)
        if not os.path.exists(final_dir_path):
            os.makedirs(final_dir_path)            
        if os.path.exists(file): 
            shutil.copy(file,final_dir_path)
    print('Completed')
    
def delete_changed_files(src_dir,delete_files):        
    print('LOG : Deleting Infected Files -> ', end='')
    os.chdir(src_dir)
    for file in delete_files:
        os.remove(file.lstrip('/'))
    print('Completed')

    
def replace_infected_files(wp_src_location,dst_dir,file_names):
    print('LOG : Replacing Infected/Missing Files -> ', end='')
    for file in file_names:
        src = os.path.join(wp_src_location,file)
        dst = os.path.join(dst_dir,file)
        shutil.copy(src,dst) 
    print('Completed')


def delete_downloads(wp_version):
    print('LOG : Deleting WordPress Source Tree -> ', end='')
    if os.path.exists(WP_SOURCE_TREE): 
        shutil.rmtree(WP_SOURCE_TREE)        
    wp_archive = '/tmp/wordpress-'+wp_version+'.zip'  
    if os.path.exists(wp_archive): 
        os.remove(wp_archive)
    print('Completed')


 
           
install_dir = sys.argv[1]
if install_dir:
    install_dir = os.path.realpath(install_dir)
    print('LOG : Directory -> ',install_dir)
    current_version = get_verison(install_dir)
    original_hash_dict = get_original_hash(current_version)
    scan_result = hash_scanner(install_dir, original_hash_dict)
    if scan_result['missing'] or scan_result['modified']:
        wp_src_download_extract(current_version)
        cur_time = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
        backup_location = install_dir+'/infected-'+cur_time
        copy_structure(backup_location,scan_result['modified'])
        delete_changed_files(install_dir,scan_result['modified'])
        replace_infected_files(WP_SOURCE_TREE,install_dir,scan_result['modified']+scan_result['missing'])   
        delete_downloads(current_version)
    else:
        print('LOG : Core Files Are Clean..!')    
else:
    print('USAGE : wphealer  /ptah/to/wp-install-dir')
    
