import os
import shutil
import subprocess

INPUT_DIR = os.path.join('jdolly_source', '0')
OUTPUT_DIR = os.path.join('data')
SOOT_JAR = os.path.join('soot', 'soot.jar')


def get_files(path, ext='.java'):

    files = []

    for node in os.listdir(path):
        node = os.path.join(path, node)
        if os.path.isdir(node):
            files += get_files(node, ext)
        elif os.path.splitext(node)[1] == ext:
            files.append(node)
 
    return files


def get_class_files(path, package='', ext='.class'):

    files = []

    for node in os.listdir(path):
        node_path = os.path.join(path, node)
        if os.path.isdir(node_path):
            package = os.path.join(package, node)
            files += get_class_files(node_path, package, ext)
        elif os.path.splitext(node_path)[1] == ext:
            files.append(os.path.join(package, node))
 
    return files


def compile(classpath, class_file=None):

    files = []

    if class_file != None:
        files.append(class_file)
    else:
        files = get_files(classpath)

    for input_file in files:
        command = ['javac', '-cp', classpath, input_file]
        subprocess.call(command, shell=False, 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)


def exec_major(class_file, classpath, mutants_dir):

    dest_dir = os.path.join(classpath, 'build', 'classes')

    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)

    os.makedirs(dest_dir)

    command = [
        'javac', 
        '-XMutator:ALL', 
        '-J-Dmajor.export.context=true', 
        '-J-Dmajor.export.mutants=true', 
        '-J-Dmajor.export.directory=' + mutants_dir,
        '-cp', classpath, 
        '-d', dest_dir,
        class_file
    ]

    return subprocess.call(command, shell=False, cwd=mutants_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)


def soot_optmizer(classpath, program_dir, java_file, class_file):
    soot_jar = os.path.abspath(SOOT_JAR)

    compile(classpath, java_file)

    rt_jar = '/usr/lib/jvm/default-jvm/jre/lib/rt.jar'

    classpath = program_dir + ':' + rt_jar + ':' + classpath

    command = ['java', '-jar', soot_jar, '-cp', classpath, '-O', class_file]

    return subprocess.call(command, shell=False, cwd=program_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)


def diff(mutant_dir, original_dir):

    opt_mutant_dir = os.path.join(mutant_dir, 'sootOutput')
    opt_original_dir = os.path.join(original_dir, 'sootOutput')

    mutants = get_class_files(opt_mutant_dir)

    equivalent = True

    for mutant in mutants:
        command = ['diff', os.path.join(opt_original_dir, mutant), os.path.join(opt_mutant_dir, mutant)]
        status = subprocess.call(command, shell=False, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)       
        if status != 0:
            equivalent = False
    
    return equivalent


def generate_mutants(test, classpath, working_dir):

    full_qualified_java = get_class_files(classpath, ext='.java')

    for java_file in full_qualified_java:     
        mutants_dir = os.path.join(working_dir, 'mutants', java_file.split('.')[0])
        class_file = os.path.join(classpath, java_file)

        if os.path.exists(mutants_dir):
            shutil.rmtree(mutants_dir)
        
        os.makedirs(mutants_dir)
    
        exec_major(class_file, classpath, mutants_dir)

        csv = open(os.path.join(mutants_dir, 'tce.csv'), 'w')
        csv.write('test,mutantNo,status\n')

        for mutant in os.listdir(mutants_dir):
            mutant_dir = os.path.join(mutants_dir, mutant)
            if os.path.isdir(mutant_dir):
                mutant_java = os.path.join(mutant_dir, java_file)
                mutant_class = java_file.split('.')[0].replace(os.sep, '.')
                soot_optmizer(classpath, mutant_dir, mutant_java, mutant_class)
                if (diff(mutant_dir, classpath)):
                    print ("!!!! Mutant " + mutant_java + " is equivalent.")
                    csv.write(test + ',' + mutant + ',' + 'TCE_CONFIRMED\n')
                else:
                    csv.write(test + ',' + mutant + ',' + 'NO\n')
        
        csv.close()


def copy_original(src, dest, test):
    dest_path = os.path.join(dest, test, 'original')

    if not os.path.exists(dest_path):
        shutil.copytree(os.path.join(src, test), dest_path)
        return dest_path

    return None   


def main():    
    input_dir = os.path.abspath(INPUT_DIR)
    output_dir = os.path.abspath(OUTPUT_DIR)

    for test_dir in os.listdir(input_dir):
        if os.path.isdir(os.path.join(input_dir, test_dir)):         
            working_dir = os.path.join(output_dir, test_dir)
            original_dir = copy_original(input_dir, output_dir, test_dir)
            
            if original_dir != None:     
                full_qualified_java = get_class_files(original_dir, ext='.java')

                for java_file in full_qualified_java:
                    class_file = java_file.split('.')[0].replace(os.sep, '.')
                    java_file = os.path.join(original_dir, java_file)

                    soot_optmizer(original_dir, original_dir, java_file, class_file)

                generate_mutants(test_dir, original_dir, working_dir)
            else:
                print("SKIPING " + test_dir)    