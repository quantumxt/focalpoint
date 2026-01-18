# Focalpoint

<a href="LICENSE" ><img src="https://img.shields.io/github/license/quantumxt/focalpoint?style=for-the-badge"/></a>

Focalpoint is a Python tool for photographers and hobbyists to analyze their photo libraries.

## Installation
Clone the repository.

```sh
git clone https://github.com/quantumxt/focalpoint.git
cd focalpoint
```

Install dependencies.

```sh
pip install -r requirements.txt
```

## Usage

### Basic

This will scan the specified directory and display interactive charts of focal length usage.

```sh
python focalpoint.py /path/to/images
```

### Save Plots

Add the `--save-plot` flag to save the visualizations as HTML and PNG.

```sh
python focalpoint.py /path/to/images --save-plot
```

* HTML file: focal_length_usage_per_lens.html
* PNG file: focal_length_usage_per_lens.png

# License
Licensed under the [MIT License](./LICENSE).
