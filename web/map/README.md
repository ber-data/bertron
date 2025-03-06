# Map

## Overview

This web page displays all samples from all projects on a single map.

By default, the entire world map is visible. You can click the `+`/`-` buttons
on the map to zoom in/out. You can click the magnifying glass button to search
by address.

Samples are grouped into clusters, where the color of the cluster indicates
whether there is a small, medium, or large number of samples in that region.

The `index.html` file, itself, is about 10 KB in size. When a web browser loads
the file and runs the JavaScript scripts within it, the web browser will fetch
an additional 1.5 MB of gzipped resources from GitHub (about 8.5 MB when unzipped).

## Technologies

This web page is built upon the following technologies:

- [Leaflet](https://leafletjs.com/) - to show the map ([BSD 2-Clause "Simplified" license](https://github.com/Leaflet/Leaflet/blob/main/LICENSE))
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) - to show map markers as clusters ([MIT license](https://github.com/Leaflet/Leaflet.markercluster/blob/master/MIT-LICENCE.txt))
- [leaflet-geosearch](https://smeijer.github.io/leaflet-geosearch/#using-a-cdn) - to add a geolocation search widget ([MIT license](https://github.com/smeijer/leaflet-geosearch/blob/main/LICENSE))
- [PapaParse](https://github.com/mholt/PapaParse) - to fetch and parse CSV files ([MIT license](https://github.com/mholt/PapaParse/blob/master/LICENSE))
- [Prettier](https://prettier.io) - to format our source code ([MIT license](https://github.com/prettier/prettier/blob/main/LICENSE))
- [Bootstrap 5](https://getbootstrap.com/) - to style the web page elements other than the map ([MIT license](https://github.com/twbs/bootstrap/blob/main/LICENSE))

## Development

### Code format

We use Prettier to format the code in this directory. You can format it by running:

```shell
# Run from this directory.
npx prettier . --write
```

### Directory structure

I opted to keep the HTML, CSS, and JavaScript in a single file to facilitate
rapid early prototyping. Before developing this beyond the prototype stage,
I'd recommend extracting the JavaScript into a separate file(s), using a
package manager such as NPM to manage JavaScript dependencies, etc.

## Roadmap (draft)

Here are some ideas I have for future development (in no particular order):

- Allow the user to toggle all markers associated with a given data source
  (e.g. NMDC vs. ESS-Dive) on/off
- Use the data source's logo instead of the generic marker image
- Add hyperlinks (leading to more information about the sample) to the marker
  popups
