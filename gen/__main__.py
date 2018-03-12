import sys
import os
import subprocess
import shutil


INPUT_DIR = sys.argv[1]
OUTPUT_DIR = sys.argv[2]


def compile(classpath, java_file, dest_dir):
    classes_dir = os.path.join(dest_dir, 'build', 'classes')

    if not os.path.exists(classes_dir):
        os.makedirs(classes_dir)

    mutant_dest = os.path.join(dest_dir, 'mutants', java_file.split('.')[0])

    if not os.path.exists(mutant_dest):
        os.makedirs(mutant_dest)

    command = [
        'javac', 
        '-XMutator:ALL', 
        '-J-Dmajor.export.context=true', 
        '-J-Dmajor.export.mutants=true', 
        '-J-Dmajor.export.directory=' + os.path.join(mutant_dest, 'mutants'),
        '-cp', classpath, '-d', classes_dir, os.path.join(classpath, java_file)
    ]

    return subprocess.call(command, shell=False, cwd=mutant_dest)


def main():
    output_dir = os.path.abspath(OUTPUT_DIR)
    input_dir = os.path.abspath(INPUT_DIR)

    print('Hello World!')

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
                            java_file_path = os.path.join(package, java_file)
                            return_code = compile(classpath=project_dir, java_file=java_file_path, dest_dir=dest_dir)

                            if return_code != 0:
                                is_valid = False
            
            if not is_valid:
                shutil.rmtree(dest_dir)

