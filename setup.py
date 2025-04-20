# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import setuptools


def run():
    setuptools.setup(
        name='SIDEKICK',
        version = findversion('.', 'sk'),
        author='LANNOCC',
        url='https://make.lanno.cc/source/sidekick',
        packages=setuptools.find_packages(),
        description='AI SideKick',
        long_description_content_type='text/markdown',
        long_description=open('README.md').read(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
        ],
        install_requires=[
            'google-genai',
            'google-generativeai',
            'gTTS', # text-to-speech (Linux)
            #'opencv-python',
            'Pillow',
            'playsound3',
            'pyautogui',
            'pyttsx3', # text-to-speech (Windows)
            'sphinx', 'sphinx-autoapi', 'piccolo-theme', # for API docs
            #'simpleaudio',
        ],
        entry_points = {
            'console_scripts': [
                'sk=sk.__main__:run',
                'sk-agent=sk.agent.__main__:run',
                'sk-action=sk.action.__main__:run',
                #'sk-ask=sk.ask.__main__:run',
                'ask=sk.__main__:run',
                'task=sk.__main__:run',
            ],
        },
    )


def findversion(root, name):
    '''versioning strategy taken from
       http://stackoverflow.com/a/7071358/7203060'''

    import re
    from os.path import join

    vfile = join(root, name, "__version__.py")
    vmatch = re.search(r'^__version__ *= *["\']([^"\']*)["\']',
        open(vfile, "rt").read(), re.M)

    if vmatch:
        version = vmatch.group(1)
        print ("Found %s version %s" % (name, version))
        return version

    else:
        raise RuntimeError("Expecting a version string in %s." % (vfile))


if __name__ == '__main__':
    run()

