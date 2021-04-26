from setuptools import setup

setup(
	name='pySDRBurstfile',
	version='0.1.0',
	author='Richard Baker',
	author_email='richard.baker@cs.ox.ac.uk',
	packages=['pySDRBurstfile'],
	#scripts=['bin/script1','bin/script2'],
	#url='http://pypi.python.org/pypi/PackageName/',
	#license='LICENSE.txt',
	description='A file format for burst SDR captures',
	long_description=open('README.md').read(),
	install_requires=[
		"numpy"
	],
)
