import os
import shutil
import subprocess

INPUT_DIR = os.path.join('jdolly_source', '0')
OUTPUT_DIR = os.path.join('data')
SOOT_JAR = os.path.join('soot', 'soot.jar')
TEST = 'test1'


def compile(classpath, class_file):
    command = ['javac', '-cp', classpath, class_file]
    return subprocess.call(command, shell=False, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)

def exec_major(class_file, classpath, mutants_dir):
    command = [
        'javac', 
        '-XMutator:ALL', 
        '-J-Dmajor.export.context=true', 
        '-J-Dmajor.export.mutants=true', 
        '-J-Dmajor.export.directory=' + mutants_dir,
        '-cp', classpath, 
        class_file
    ]

    return subprocess.call(command, shell=False, cwd=mutants_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)

def soot_optmizer_original(process_dir):
    soot_jar = os.path.abspath(SOOT_JAR)
    command = ['java', '-jar', soot_jar, '-process-dir', process_dir]

    return subprocess.call(command, shell=False, cwd=process_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)


def soot_optmizer_mutant(classpath, mutant_dir, mutant_java, mutant_class):
    soot_jar = os.path.abspath(SOOT_JAR)

    compile(classpath, mutant_java)

    rt_jar = '/usr/lib/jvm/default-jvm/jre/lib/rt.jar'
    classpath = mutant_dir + ':' + rt_jar + ':' + os.path.join(classpath, 'sootOutput')

    command = ['java', '-jar', soot_jar, '-cp', classpath, '-O', mutant_class]

    return subprocess.call(command, shell=False, cwd=mutant_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)


def generate_mutants(classpath, working_dir):
    package = 'Package_0'
    class_java = 'Class_0.java' 

    mutants_dir = os.path.join(working_dir, 'mutants', package, class_java.split('.')[0])
    class_file = os.path.join(classpath, package, class_java)

    if os.path.exists(mutants_dir):
        shutil.rmtree(mutants_dir)
    os.makedirs(mutants_dir)
    
    exec_major(class_file, classpath, mutants_dir)

    for mutant in os.listdir(mutants_dir):
        mutant_dir = os.path.join(mutants_dir, mutant)
        if os.path.isdir(mutant_dir):
            mutant_java = os.path.join(mutant_dir, package, class_java)
            mutant_class = package.replace(os.sep, '.') + '.' + class_java.split('.')[0]
            soot_optmizer_mutant(classpath, mutant_dir, mutant_java, mutant_class)


def copy_original(src, dest, test):
    dest_path = os.path.join(dest, test, 'original')

    if not os.path.exists(dest_path):
        shutil.copytree(os.path.join(src, test), dest_path)
        return dest_path

    return None   


def main():    
    input_dir = os.path.abspath(INPUT_DIR)
    output_dir = os.path.abspath(OUTPUT_DIR)
        
    working_dir = os.path.join(output_dir, TEST)
    original_dir = copy_original(input_dir, output_dir, TEST)
    
    if original_dir != None:   
        soot_optmizer_original(original_dir)   
        generate_mutants(original_dir, working_dir)
    else:
        print("SKIPING " + TEST)