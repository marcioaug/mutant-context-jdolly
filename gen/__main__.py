import sys
import os
import subprocess
import shutil


INPUT_DIR = sys.argv[1]
OUTPUT_DIR = sys.argv[2]
SOOT_JAR = sys.argv[3]

def compile(classpath, package, java_file, dest_dir):
    classes_dir = os.path.join(dest_dir, 'build', 'classes')
    java_file_path = os.path.join(package, java_file)
    src_dir = os.path.join(dest_dir, 'src', package)
    
    if not os.path.exists(classes_dir):
        os.makedirs(classes_dir)

    if not os.path.exists(src_dir):
        os.makedirs(src_dir)

    shutil.copy(os.path.join(classpath, java_file_path), src_dir)

    mutant_dest = os.path.join(dest_dir, 'mutants', java_file_path.split('.')[0])

    if not os.path.exists(mutant_dest):
        os.makedirs(mutant_dest)

    command = [
        'javac', 
        '-XMutator:ALL', 
        '-J-Dmajor.export.context=true', 
        '-J-Dmajor.export.mutants=true', 
        '-J-Dmajor.export.directory=' + os.path.join(mutant_dest, 'mutants'),
        '-cp', classpath, '-d', classes_dir, os.path.join(classpath, java_file_path)
    ]

    return subprocess.call(command, shell=False, cwd=mutant_dest, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)


def soot(process_dir):
    soot_jar = os.path.abspath(SOOT_JAR)
    command = ['java', '-jar', soot_jar, '-process-dir', process_dir]

    return subprocess.call(command, shell=False, cwd=process_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)

def soot_cp(original_dir, process_dir):
    soot_jar = os.path.abspath(SOOT_JAR)

    rt_jar = '/usr/lib/jvm/default-jvm/jre/lib/rt.jar'
    classpath = original_dir + ':' + rt_jar

    command = ['java', '-jar', soot_jar, '-cp', classpath, '-process-dir', process_dir]

    return subprocess.call(command, shell=False, cwd=process_dir, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)


def diff(original_dir, mutant_dir, dest_dir):

    is_equivalent = True
    
    for package in os.listdir(mutant_dir):

        if package != 'sootOutput':
            original_package_dir = os.path.join(original_dir, package)
            mutant_package_dir = os.path.join(mutant_dir, package)

            for class_file in os.listdir(mutant_package_dir):
                original_class_file = os.path.join(original_package_dir, class_file)
                mutant_class_file = os.path.join(mutant_package_dir, class_file)
                command = ['diff', original_class_file, mutant_class_file]
                status = subprocess.call(command, shell=False, 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)

                if status != 0:
                    is_equivalent = False

    return is_equivalent


def tce(data_dir):

    all_tce_file = os.path.join(data_dir, 'tce.csv')
    all_csv = open(all_tce_file, 'w', 1)
    all_csv.write("program,mutantNo,TCE\n")

    for program in os.listdir(data_dir):
        test_dir = os.path.join(data_dir, program)
        if os.path.isdir(test_dir):
            src_dir = os.path.join(test_dir, 'src')
            soot(src_dir)
            original_dir = os.path.join(src_dir, 'sootOutput')
            mutants_dir = os.path.join(test_dir, 'mutants')
            for package in os.listdir(mutants_dir):
                package_dir = os.path.join(mutants_dir, package)
                for class_dir in os.listdir(package_dir):   
                    class_mutant_dir = os.path.join(package_dir, class_dir, 'mutants')
                    tce_file = os.path.join(package_dir, class_dir, 'tce.csv')
                    csv = open(tce_file, 'w')

                    csv.write("program,mutantNo,TCE\n")

                    for mutant_dir in os.listdir(class_mutant_dir):
                        process_dir = os.path.join(class_mutant_dir, mutant_dir)
                        soot_cp(original_dir, process_dir)
                        mutant_soot_dir = os.path.join(process_dir, 'sootOutput')
                        if diff(original_dir, mutant_soot_dir, class_mutant_dir):
                            csv.write(program + ',' + mutant_dir + ',CONFIRMED\n')
                            all_csv.write(program + ',' + mutant_dir + ',CONFIRMED\n')
                        else:
                            csv.write(program + ',' + mutant_dir + ',NO\n')
                            all_csv.write(program + ',' + mutant_dir + ',NO\n')

                    csv.close()
    all_csv.close()


def main():
    output_dir = os.path.abspath(OUTPUT_DIR)
    input_dir = os.path.abspath(INPUT_DIR)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for file in os.listdir(input_dir):
        list_dir = os.path.join(input_dir, file)

        if os.path.isdir(list_dir):

            is_valid = True
            dest_dir = os.path.join(output_dir, file)

            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)

            os.makedirs(dest_dir)

            for test_dir in os.listdir(list_dir):
                in_dir = os.path.join(input_dir, list_dir, test_dir)
                if os.path.isdir(in_dir) and test_dir == 'in':
                    project_dir = in_dir
                    for package in os.listdir(project_dir):
                        package_dir = os.path.join(project_dir, package)
                        for java_file in os.listdir(package_dir):
                            return_code = compile(classpath=project_dir, package=package, java_file=java_file, dest_dir=dest_dir)

                            if return_code != 0:
                                is_valid = False
            
            if not is_valid:
                shutil.rmtree(dest_dir)

    tce(data_dir=output_dir)
