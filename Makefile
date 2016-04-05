test:
	nosetests --with-coverage --cover-html --cover-package=prospyr --cover-erase --rednose

upload:
	python setup.py sdist bdist_wheel && \
	twine upload dist/* --sign --repository=pypi; \
	rm -rf build dist prospyr.egg-info
