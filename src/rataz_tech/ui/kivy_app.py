from __future__ import annotations

import os
from datetime import datetime

from rataz_tech.core.models import DocumentInput, QueryRequest
from rataz_tech.main import build_pipeline

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.spinner import Spinner
    from kivy.uix.textinput import TextInput
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Kivy is not installed. Install UI extras with: pip install -e '.[ui]'"
    ) from exc


class RefineryUI(BoxLayout):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(orientation="vertical", spacing=8, padding=8, **kwargs)
        config_path = os.environ.get("RATAZ_TECH_CONFIG", "configs/settings.yaml")
        self.pipeline = build_pipeline(config_path)

        self.add_widget(Label(text="Rataz Tech Refinery-OS (Kivy UI)", size_hint_y=None, height=34))

        self.doc_input = TextInput(
            hint_text="Paste document text here...",
            multiline=True,
            size_hint_y=0.35,
        )
        self.add_widget(self.doc_input)

        ingest_btn = Button(text="Ingest Document", size_hint_y=None, height=40)
        ingest_btn.bind(on_press=self.ingest_document)
        self.add_widget(ingest_btn)

        self.query_input = TextInput(
            hint_text="Enter query...",
            multiline=False,
            size_hint_y=None,
            height=40,
        )
        self.add_widget(self.query_input)

        self.lang_spinner = Spinner(
            text="am",
            values=("am", "en"),
            size_hint_y=None,
            height=40,
        )
        self.add_widget(self.lang_spinner)

        query_btn = Button(text="Run Query", size_hint_y=None, height=40)
        query_btn.bind(on_press=self.run_query)
        self.add_widget(query_btn)

        self.output = TextInput(readonly=True, multiline=True, size_hint_y=0.4)
        self.add_widget(self.output)

    def ingest_document(self, *_: object) -> None:
        doc_text = self.doc_input.text.strip()
        if not doc_text:
            self.output.text = "Document text is required."
            return

        doc_id = f"ui-doc-{int(datetime.utcnow().timestamp())}"
        doc = DocumentInput(
            document_id=doc_id,
            source_uri="ui://manual-input",
            content=doc_text,
        )
        result = self.pipeline.ingest(doc)
        self.output.text = result.model_dump_json(indent=2, ensure_ascii=False)

    def run_query(self, *_: object) -> None:
        query_text = self.query_input.text.strip()
        if not query_text:
            self.output.text = "Query text is required."
            return

        response = self.pipeline.query(
            QueryRequest(
                query=query_text,
                language=self.lang_spinner.text,
                max_results=self.pipeline.settings.pipeline.max_query_results,
            )
        )
        self.output.text = response.model_dump_json(indent=2, ensure_ascii=False)


class RefineryKivyApp(App):
    def build(self) -> RefineryUI:
        self.title = "Rataz Tech Refinery UI"
        return RefineryUI()


def run_ui() -> None:
    RefineryKivyApp().run()


if __name__ == "__main__":
    run_ui()
