# DeepGIS

DeepGIS is an annotation tool for images like cameratraps, UAV imagery, satellite images.
It is widely used for annotation, learning and introspection of semantic maps.

DeepGIS is developed using the following technologies
- [Django Web Framework](https://www.djangoproject.com/)
- [Docker](https://www.docker.com/)
- [Paper.js](http://paperjs.org/)
- [PostgreSQL](https://www.postgresql.org/)

## Installation
```console 
foo@bar:~$ git clone https://github.com/DREAMS-lab/deepgis.git
foo@bar:~$ cd deepgis
foo@bar:~$ docker-compose up
```

## Configuration
### Add a super user in DeepGIS
```bash 
foo@bar:~$ docker exec -it deepgis_web_1 bash
foo@bar:~$ python manage.py createsuperuser
```

### Add images to DeepGIS
We have provided a few test images in `webclient/static/small-tomatoes` directory.

```bash 
foo@bar:~$ python manage.py runscript injectImages /app/webclient/static/small-tomatoes/
foo@bar:~$ python manage.py collectstatic
```

### Viewing labels
Labels are stored in the folder specified in the settings file, default being 'labels', which should be in the `static-root` folder. Labels can also be inspected through the web app using the admin image labels page.

### UI Controls
You can resize the browser using standard browser controls (Ctrl+ and Ctrl-). Additionally, the app has sliders to control brightness, contrast, and hue. Adjust these to make the target objects clearer.

Labels can be moved by dragging, and deleted by double-clicking.
Choose 'No labels in image' option when there are no labels in the image.
Submit when finished labeling an image.

## Usage
The webapp is be serving at [localhost:8000](http://localhost:8000).
The admin page is available at [localhost:8000/admin](http://localhost:8000/admin)

## Visuals


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Authors and Acknowledgment

**Affiliation: [Prof. Jnaneshwar "JD" Das](https://sese.asu.edu/node/3438 "Jnaneshwar Das"), [Distributed Robotic Exploration and Mapping Systems Laboratory](https://web.asu.edu/jdas), ASU School of Earth and Space Exploration**

This project is derived from [AgDSS](https://github.com/Trefo/agdss)

## License
[Apache License 2.0](https://github.com/DREAMS-lab/deepgis/blob/master/LICENSE)

## Project Status
Active 
