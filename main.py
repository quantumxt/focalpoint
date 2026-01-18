import os
import math
import string
from collections import Counter, defaultdict
import argparse

from PIL import Image, ExifTags

# import matplotlib.pyplot as plt
import plotly.graph_objects as go
import kaleido

class ImageFile:
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}

    def __init__(self, img_path: str):
        self.lens_model = None
        self.focal_len = None
        self.aperture = None
        exif_data = self.extract_exif(img_path)
        if exif_data is not None:
            self.lens_model, self.focal_len, self.aperture = exif_data

    def extract_exif(self, image_path: str) -> (str, float, float):
        try:
            with Image.open(image_path) as img:
                exif = img._getexif()

            if not exif:
                return None

            exif_data = {
                ExifTags.TAGS.get(tag, tag): value
                for tag, value in exif.items()
            }

            focal_len = exif_data.get("FocalLength")
            aperture = exif_data.get("FNumber")
            lens_model = exif_data.get("LensModel", "Unknown Lens")

            if focal_len is not None:
                focal_len = self._to_float(exif_data.get("FocalLength"))
            if aperture is not None:
                aperture = self._to_float(exif_data.get("FNumber"))

            lens_model = self.remove_non_ascii(str(lens_model))

            return lens_model, focal_len, aperture

        except Exception:
            return None

    def remove_non_ascii(self, text: str) -> str:
        ascii_chars = set(string.printable)
        return ''.join(c for c in text if c in ascii_chars)

    def _to_float(self, value):
        try:
            if isinstance(value, tuple):
                return value[0] / value[1]
            return float(value)
        except Exception:
            return None

class ImageAnalysis:
    def __init__(self, dir_path):
        if not os.path.isdir(dir_path):
            print("Invalid directory path.")
            return

        by_dir = self.scan_directory(dir_path)

        if not by_dir:
            print("No valid EXIF data found.")
            return

        summary = self.directory_lens_summary(by_dir)
        self.print_directory_lens_summary(summary)

        overview = self.overall_overview(by_dir)
        self.print_overall_overview(overview)

        # self.plot_lens_focal_scatter(by_dir)
        self.plot_lens_focal_interactive(by_dir)

    def scan_directory(self, directory) -> dict:
        by_dir = defaultdict(lambda: defaultdict(list))

        for root, _, files in os.walk(directory):
            dir_name = os.path.relpath(root, directory)

            for file in files:
                if os.path.splitext(file)[1].lower() in ImageFile.SUPPORTED_EXTENSIONS:
                    img = ImageFile(os.path.join(root, file))
                    if img.lens_model == "Unknown Lens":
                        continue
                    if img:
                        if img.focal_len and img.aperture:
                            by_dir[dir_name][img.lens_model].append((img.focal_len, img.aperture))
        return by_dir

    def top_n_values(self, counter, n=5):
        if not counter:
            return []

        items = counter.most_common()
        if len(items) <= n:
            return items

        cutoff = items[n - 1][1]
        return [(v, c) for v, c in items if c >= cutoff]

    def directory_lens_summary(self, by_dir):
        summary = {}

        for dir_name, lenses in by_dir.items():
            lens_stats = []

            for lens, data in lenses.items():
                total_images = len(data)
                apertures = Counter(a for f, a in data)
                focals = Counter(f for f, a in data)

                lens_stats.append({
                    "Lens": lens,
                    "Total Images": total_images,
                    "Top Apertures": [
                        f"f/{a} ({c})" for a, c in self.top_n_values(apertures, 5)
                    ],
                    "Top Focal Lengths": [
                        f"{f}mm ({c})" for f, c in self.top_n_values(focals, 5)
                    ],
                })

            lens_stats.sort(key=lambda x: x["Total Images"], reverse=True)
            summary[dir_name] = lens_stats

        return summary

    def print_directory_lens_summary(self, summary):
        print("\n=== Lens Usage Summary ===\n")

        for dir_name, lenses in summary.items():
            print(f"\nDirectory: {dir_name}")
            print("=" * (14 + len(dir_name)))

            for lens in lenses:
                print(f"\nLens: {lens['Lens']}")
                print(f"Total Images: {lens['Total Images']}")
                print(f"Top Apertures: {', '.join(lens['Top Apertures'])}")
                print(f"Top Focal Lengths: {', '.join(lens['Top Focal Lengths'])}")

            print("\n" + "-" * 70)

    def overall_overview(self, by_dir):
        """
        Aggregate stats across ALL directories
        """
        lens_data = defaultdict(list)

        for lenses in by_dir.values():
            for lens, data in lenses.items():
                lens_data[lens].extend(data)

        overview = []

        for lens, data in lens_data.items():
            apertures = Counter(a for f, a in data)
            focals = Counter(f for f, a in data)

            overview.append({
                "Lens": lens,
                "Total Images": len(data),
                "Top Apertures": [
                    f"f/{a} ({c})" for a, c in self.top_n_values(apertures, 5)
                ],
                "Top Focal Lengths": [
                    f"{f}mm ({c})" for f, c in self.top_n_values(focals, 5)
                ],
            })

        overview.sort(key=lambda x: x["Total Images"], reverse=True)
        return overview


    def print_overall_overview(self, overview):
        print("\nOVERALL LENS OVERVIEW (All Directories)")
        print("=" * 45)

        total_images = sum(item["Total Images"] for item in overview)
        print(f"\nTotal Images Analysed: {total_images}\n")

        for item in overview:
            print(f"Lens: {item['Lens']}")
            print(f"Total Images: {item['Total Images']}")
            print(f"Top Apertures: {', '.join(item['Top Apertures'])}")
            print(f"Top Focal Lengths: {', '.join(item['Top Focal Lengths'])}")
            print("-" * 60)

    def plot_lens_focal_scatter(self, by_dir, size_scale=20):
        """
        Bubble scatter plot:
        X = focal length
        Y = lens
        Bubble size = frequency of focal length usage
        X-axis ticks every 10mm
        """
        lens_focal_counts = defaultdict(Counter)
        all_focals = []

        # Collect data
        for lenses in by_dir.values():
            for lens, data in lenses.items():
                for focal, _ in data:
                    if focal is not None:
                        lens_focal_counts[lens][focal] += 1
                        all_focals.append(focal)

        if not lens_focal_counts:
            print("No focal length data to plot.")
            return

        lenses = list(lens_focal_counts.keys())
        y_positions = range(len(lenses))

        plt.figure(figsize=(12, max(6, len(lenses) * 0.6)))

        for y, lens in zip(y_positions, lenses):
            focals = list(lens_focal_counts[lens].keys())
            freqs = list(lens_focal_counts[lens].values())

            plt.scatter(
                focals,
                [y] * len(focals),
                s=[f * size_scale for f in freqs],
                alpha=0.6
            )

        # X-axis ticks every 10mm
        min_focal = int(min(all_focals) // 10 * 10)
        max_focal = int((max(all_focals) // 10 + 1) * 10)
        xticks = list(range(min_focal, max_focal + 1, 10))

        plt.xticks(xticks, [f"{x}mm" for x in xticks])

        plt.yticks(y_positions, lenses)
        plt.xlabel("Focal Length (mm)")
        plt.ylabel("Lens")
        plt.title("Focal Length Usage per Lens (Bubble Size = Frequency)")
        plt.grid(axis="x", linestyle="--", alpha=0.5)

        plt.tight_layout()
        plt.show()

    def plot_lens_focal_interactive(self, by_dir, save=False, size_scale=10):
        """
        Interactive bubble chart:
        X = focal length
        Y = lens
        Bubble size = frequency
        """
        lens_focal_counts = defaultdict(Counter)
        all_focals = []

        # Collect data
        for lenses in by_dir.values():
            for lens, data in lenses.items():
                for focal, _ in data:
                    if focal is not None:
                        lens_focal_counts[lens][focal] += 1
                        all_focals.append(focal)

        if not lens_focal_counts:
            print("No focal length data to plot.")
            return

        fig = go.Figure()
        for lens, counter in lens_focal_counts.items():
            focals = list(counter.keys())
            freqs = list(counter.values())

            fig.add_trace(
                go.Scatter(
                    x=focals,
                    y=[lens] * len(focals),
                    mode="markers",
                    name=lens,
                    marker=dict(
                        size=[math.sqrt(f) * 8 for f in freqs],
                        opacity=0.7
                    ),
                    hovertemplate=(
                        "<b>Lens:</b> %{y}<br>"
                        "<b>Focal:</b> %{x} mm<br>"
                        "<b>Images:</b> %{marker.size:.0f}<extra></extra>"
                    )
                )
            )

        # X-axis ticks every 10mm
        min_focal = int(min(all_focals) // 10 * 10)
        max_focal = int((max(all_focals) // 10 + 1) * 10)

        fig.update_layout(
            title="Focal Length Usage per Lens",
            xaxis=dict(
                title="Focal Length (mm)",
                tickmode="linear",
                tick0=min_focal,
                dtick=10
            ),
            yaxis=dict(
                title="Lens",
                type="category"
            ),
            legend_title="Lens",
            height=max(400, 80 * len(lens_focal_counts)),
            margin=dict(l=200)
        )

        if save:
            fig.write_html("lens_focal_usage.html")
            fig.write_image("lens_focal_usage.png", width=1600, height=900, scale=2)
            print("Plots saved as lens_focal_usage.html/png")
        else:
            fig.show()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", help="Path to image directory")
    parser.add_argument(
        "--save-plot",
        help="Save plots to files",
        action="store_true"
    )
    args = parser.parse_args()
    analysis = ImageAnalysis(args.dir)

    if args.save_plot:
        analysis.plot_lens_focal_interactive(analysis.scan_directory(args.dir), save=True)

if __name__ == "__main__":
    main()
