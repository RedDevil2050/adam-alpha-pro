import os
import time
import streamlit as st
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.toml'):
            if hasattr(st, 'session_state'):
                st.session_state.config_changed = True

def start_config_monitor():
    config_path = os.path.expanduser('~/.streamlit')
    event_handler = ConfigFileHandler()
    observer = Observer()
    observer.schedule(event_handler, config_path, recursive=False)
    observer.start()
    return observer
