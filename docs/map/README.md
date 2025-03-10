# BERtron map

## Overview

This web page displays all samples from all data sources on a single map.

By default, the entire world map is visible. You can click the `+`/`-` buttons
on the map to zoom in/out. You can click the magnifying glass button to search
by address.

Samples are grouped into clusters based upon their geolocation, regardless of
the data source. The color of the cluster indicates whether there is a small,
medium, or large number of samples in that region.

The `index.html` file, itself, is about 15 KB in size. When a web browser loads
the file and executes the JavaScript code within it, the web browser will fetch
geolocation data files from GitHub and various CSS/JavaScript assets from a CDN.

## Technologies

This web page is built upon the following technologies:

- [Bootstrap 5](https://getbootstrap.com/) - to style the web page elements other than the map ([MIT license](https://github.com/twbs/bootstrap/blob/main/LICENSE))
- [Leaflet](https://leafletjs.com/) - to show the map ([BSD 2-Clause "Simplified" license](https://github.com/Leaflet/Leaflet/blob/main/LICENSE))
- [Leaflet.FeatureGroup.SubGroup](https://github.com/ghybs/Leaflet.FeatureGroup.SubGroup) - to allow users to toggle the visibility of markers from a given data source while allowing any given cluster to contain markers associated with multiple data sources ([BSD 2-Clause "Simplified" license](https://github.com/ghybs/Leaflet.FeatureGroup.SubGroup/blob/master/LICENSE))
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) - to group map markers into clusters ([MIT license](https://github.com/Leaflet/Leaflet.markercluster/blob/master/MIT-LICENCE.txt))
- [leaflet-geosearch](https://smeijer.github.io/leaflet-geosearch/#using-a-cdn) - to add a geolocation search widget ([MIT license](https://github.com/smeijer/leaflet-geosearch/blob/main/LICENSE))
- [PapaParse](https://github.com/mholt/PapaParse) - to fetch and parse CSV files ([MIT license](https://github.com/mholt/PapaParse/blob/master/LICENSE))

## Development

### Development tools

- [Fonticon](https://gauger.io/fonticon/) - to generate a favicon from a [Font Awesome](https://fontawesome.com/v4/license/) icon
- [Prettier](https://prettier.io) - to format source code ([MIT license](https://github.com/prettier/prettier/blob/main/LICENSE))
- [Vite](https://vite.dev/guide/cli.html#dev-server) - to serve data locally during development ([MIT license](https://github.com/vitejs/vite/blob/main/LICENSE))

### Development server

This web page uses assets that reside in this repository.

When this web page is being served by GitHub Pages, the web page fetches
those assets from the GitHub repository—meaning it is subject to any rate
limiting GitHub might have in place (I don't know whether it has any).

In order to eliminate the possibility of hitting any rate limits while
developing the web page locally, you can put the web page into its
"development mode," in which it will fetch those assets from a local
web server serving the contents of this repository.

You can activate "development mode" by running the following commands,
then visiting: http://localhost:4000/docs/map/index.html

```shell
# Go to the directory containing this file.
cd docs/map/

# Start a web server that will serve the root directory of this repository.
npx vite serve --port 4000 ../../
```

> Note: Although the port number that the server listens on can be customized, the web page,
> itself, will only go into "development mode" when the port number is `4000`.

That web server will serve the entire contents of the repository, which includes the assets
(i.e. CSV/JSON data files) that the web page fetches.

### Code format

We use Prettier to format the code in this directory. You can format it by running:

```shell
# Go to the directory containing this file.
cd docs/map/

# Format the files in this directory.
npx prettier . --write
```

### Directory structure

We opted to keep the HTML, CSS, and JavaScript in a single file to facilitate
rapid early prototyping.

Before developing this beyond the prototype stage, we'd recommend extracting the
JavaScript code into a separate file(s), switching from JavaScript to TypeScript,
using a package manager such as NPM to manage JavaScript dependencies, using a
build tool such as Vite to transpile code from TypeScript to JavaScript, etc.
