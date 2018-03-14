import os
import shutil
import subprocess
import re


INPUT_DIR = os.path.join('jdolly_source', '0')
OUTPUT_DIR = os.path.join('data')
SOOT_JAR = os.path.join('soot', 'soot.jar')


def sort_files(files):
    return sorted(files, key=lambda x: (int(0 if re.sub(r'[^0-9]+','',x) == '' else re.sub(r'[^0-9]+','',x)),x))


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


def compile(classpath, program_dir, files):

    command = ['javac', '-cp', classpath]

    for input_file in files:
        command.append(os.path.join(program_dir, input_file))

    return subprocess.call(command, shell=False, 
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


def soot_optmizer(classpath, program_dir, java_files):
    soot_jar = os.path.abspath(SOOT_JAR)

    return_code = compile(classpath, program_dir, java_files)

    for java_file in java_files:
            class_file = java_file.split('.')[0].replace(os.sep, '.')
            java_file = os.path.join(program_dir, java_file)

            rt_jar = '/usr/lib/jvm/default-jvm/jre/lib/rt.jar'

            classpath = program_dir + ':' + rt_jar + ':' + classpath

            command = ['java', '-jar', soot_jar, '-cp', classpath, '-O', class_file]

            subprocess.call(command, shell=False, cwd=program_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
    
    return return_code


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
    print('-' * 80)
    print('> GENERATING MUTANTS AND CHECKING EQUIVALENCE FOR %s...' % test)

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

        total_mutants = len([dir for dir in os.listdir(mutants_dir) if os.path.isdir(os.path.join(mutants_dir, dir))])

        print('%s -> %d MUTANTS GENERATED FOR %s' % (test, total_mutants, java_file))

        count = 1
        equivante_count = 0

        for mutant in sort_files(os.listdir(mutants_dir)):            
            mutant_dir = os.path.join(mutants_dir, mutant)
            if os.path.isdir(mutant_dir):
                print('%s -> RUNNING TCE FOR %d OF %d MUTANTS.' % (test, count, total_mutants))
                count += 1
                
                if soot_optmizer(classpath, mutant_dir, [java_file]) == 0:
                    if (diff(mutant_dir, classpath)):
                        
                        print ('!!!! %s -> MUTANT %s (%s) IS EQUIVALENT. %s' % (test, mutant, java_file, ('< ' * 10)))
                        
                        equivante_count += 1
                        csv.write(test + ',' + mutant + ',' + 'TCE_CONFIRMED\n')
                    else:
                        csv.write(test + ',' + mutant + ',' + 'NOT_CONFIRMED\n')
                else:
                    print('%s ERROR -> MUTANT %s DONT COMPILE.' % (test, mutant))
                    csv.write(test + ',' + mutant + ',' + 'DONT_COMPILE\n')
        
        csv.close()

        print('EQUIVALENCE ANALISIS FOR %s FINISH. %d EQUIVALENT(S) OF %d' % (test, equivante_count, total_mutants))
        print('-' * 80)


def copy_original(src, dest, test):
    dest_path = os.path.join(dest, test, 'original')

    if not os.path.exists(dest_path):
        shutil.copytree(os.path.join(src, test, 'in'), dest_path)
        return dest_path

    return None   


def main():    
    input_dir = os.path.abspath(INPUT_DIR)
    output_dir = os.path.abspath(OUTPUT_DIR)

    for test_dir in sort_files(os.listdir(input_dir)):
        if os.path.isdir(os.path.join(input_dir, test_dir)):         
            working_dir = os.path.join(output_dir, test_dir)
            original_dir = copy_original(input_dir, output_dir, test_dir)
            
            if original_dir != None:     
                full_qualified_java = get_class_files(original_dir, ext='.java')

                if soot_optmizer(original_dir, original_dir, full_qualified_java) != 0:
                    shutil.rmtree(os.path.join(output_dir, test_dir))    
                else:
                    generate_mutants(test_dir, original_dir, working_dir)
            else:
                print("SKIPING " + test_dir)    