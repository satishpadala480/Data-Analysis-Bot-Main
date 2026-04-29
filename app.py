from flask import Flask, render_template, request, send_file
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Folders used in the project
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"

# File where cleaned data will be saved
CLEANED_FILE = os.path.join(UPLOAD_FOLDER, "cleaned_data.csv")

# Create required folders automatically if they are missing
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def home():
    # Default values before uploading a file
    rows = None
    columns = None
    column_names = None
    missing_values = None
    duplicate_count = None
    data_preview = None
    statistics = None
    graph_path = None
    insights = []
    error = None
    download_ready = False

    if request.method == "POST":
        try:
            # Get uploaded file from user
            uploaded_file = request.files.get("file")

            if uploaded_file is None or uploaded_file.filename == "":
                error = "Please upload a CSV file."
                return render_template("index.html", error=error)

            if not uploaded_file.filename.endswith(".csv"):
                error = "Only CSV files are allowed."
                return render_template("index.html", error=error)

            # Save uploaded CSV file
            safe_filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
            uploaded_file.save(file_path)

            # Read CSV file using pandas
            try:
                data = pd.read_csv(file_path)
            except UnicodeDecodeError:
                data = pd.read_csv(file_path, encoding="latin1")

            # Get user-selected options
            sort_column = request.form.get("sort_column")
            graph_column = request.form.get("graph_column")
            graph_type = request.form.get("graph_type")
            remove_missing = request.form.get("remove_missing")

            # Remove rows with missing values if user selects checkbox
            if remove_missing == "yes":
                data = data.dropna()

            # Sort data if user enters a valid column name
            if sort_column and sort_column in data.columns:
                data = data.sort_values(by=sort_column)

            # Save cleaned/modified data for download
            data.to_csv(CLEANED_FILE, index=False)
            download_ready = True

            # Basic dataset information
            rows = data.shape[0]
            columns = data.shape[1]
            column_names = list(data.columns)
            missing_values = data.isnull().sum().to_dict()
            duplicate_count = int(data.duplicated().sum())

            # Show first 10 rows
            data_preview = data.head(10).to_html(classes="table", index=False)

            # Select only numeric columns for statistics and graph
            numeric_data = data.select_dtypes(include="number")
            numeric_columns = list(numeric_data.columns)

            if not numeric_data.empty:
                statistics = numeric_data.describe().to_html(classes="table")

                # Choose graph column
                if graph_column in numeric_columns:
                    selected_column = graph_column
                else:
                    selected_column = numeric_columns[0]

                # Create graph
                plt.figure(figsize=(8, 4))

                if graph_type == "line":
                    data[selected_column].head(20).plot(kind="line", marker="o")
                    plt.title(f"Line Chart of {selected_column}")

                elif graph_type == "hist":
                    data[selected_column].plot(kind="hist", bins=10)
                    plt.title(f"Histogram of {selected_column}")

                else:
                    data[selected_column].head(20).plot(kind="bar")
                    plt.title(f"Bar Chart of {selected_column}")

                plt.xlabel("Index")
                plt.ylabel(selected_column)
                plt.tight_layout()

                graph_path = "static/graph.png"
                plt.savefig(graph_path)
                plt.close()

                # Create simple automatic insights
                for column in numeric_columns:
                    average = round(numeric_data[column].mean(), 2)
                    minimum = numeric_data[column].min()
                    maximum = numeric_data[column].max()

                    insights.append(
                        f"In column '{column}', the average value is {average}, "
                        f"minimum value is {minimum}, and maximum value is {maximum}."
                    )

            else:
                statistics = "No numeric columns found for statistics and graph."
                numeric_columns = []
                insights.append("This dataset does not contain numeric columns.")

            # Missing value insight
            total_missing = sum(missing_values.values())

            if total_missing > 0:
                insights.append(f"The dataset has {total_missing} missing values.")
            else:
                insights.append("The dataset has no missing values.")

            # Duplicate row insight
            if duplicate_count > 0:
                insights.append(f"The dataset has {duplicate_count} duplicate rows.")
            else:
                insights.append("The dataset has no duplicate rows.")

            return render_template(
                "index.html",
                rows=rows,
                columns=columns,
                column_names=column_names,
                missing_values=missing_values,
                duplicate_count=duplicate_count,
                data_preview=data_preview,
                statistics=statistics,
                graph_path=graph_path,
                insights=insights,
                numeric_columns=numeric_columns,
                download_ready=download_ready,
                error=error
            )

        except Exception as e:
            error = str(e)

    return render_template("index.html", error=error)


@app.route("/download")
def download_file():
    # Allows user to download cleaned CSV file
    if os.path.exists(CLEANED_FILE):
        return send_file(CLEANED_FILE, as_attachment=True)

    return "No cleaned file available. Please upload and analyze a CSV first."


if __name__ == "__main__":
    app.run(debug=True)