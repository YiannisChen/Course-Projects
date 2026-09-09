from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "examples" / "sample_collisions.csv"


def _uploaded_app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.file_uploader[0].upload("sample_collisions.csv", FIXTURE_PATH.read_bytes(), "text/csv")
    return app.run(timeout=30)


def test_upload_landing_state_requires_a_csv():
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    assert not app.exception
    assert [message.value for message in app.info] == [
        "Upload a compatible LA traffic-collision CSV to begin the analysis."
    ]


def test_single_year_fixture_renders_every_analysis_mode_without_errors():
    app = _uploaded_app()

    for algorithm in ["DBSCAN (Grid Patterns)", "K-Means (Record Patterns)", "Compare Grid Clustering"]:
        app.selectbox[0].set_value(algorithm)
        app.run(timeout=30)
        assert not app.exception
        assert app.metric
