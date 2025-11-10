# gui_components/parameter_controls.py

from PyQt5.QtWidgets import QWidget, QFormLayout, QSlider, QLabel, QHBoxLayout, QComboBox, QCheckBox, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtCore import Qt
from functools import partial
import logging


class ParameterControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.form_layout = QFormLayout()
        self.setLayout(self.form_layout)
        self.controls = {}  # Store controls per parameter

    def update_parameters(self, parameters, current_params, callback):
        """
        Updates the parameter controls dynamically based on the selected style.

        Args:
            parameters (list): List of parameter definitions.
            current_params (dict): Current parameter values.
            callback (function): Function to call when a parameter is updated.
        """
        logging.debug("Clearing existing controls...")
        self.clear_layout()

        self.controls = {}  # Reset controls dictionary

        # Retrieve current color_mode to handle RGB sliders later
        color_mode = current_params.get("color_mode", "White")  # Default to White

        for param in parameters:
            label = QLabel(param.get("label", "Unknown Parameter"))

            if param["type"] in ["int", "float"]:
                logging.debug(f"Adding slider for parameter: {param['name']}")
                self._add_slider_control(param, current_params, callback, label)

            elif param["type"] == "str" and "options" in param:
                logging.debug(f"Adding combobox for parameter: {param['name']}")
                self._add_combobox_control(param, current_params, callback, label)

            elif param["type"] == "bool":
                logging.debug(f"Adding checkbox for parameter: {param['name']}")
                self._add_checkbox_control(param, current_params, callback, label)

            # Add file path picker for 'file' type parameters
            elif param["type"] == "file":
                logging.debug(f"Adding file picker for parameter: {param['name']}")
                self._add_file_picker_control(param, current_params, callback, label)

            else:
                logging.warning(f"Unsupported parameter type: {param['type']}")

        # Ensure RGB sliders are enabled only if color_mode is "Custom"
        is_custom = color_mode == "Custom"
        for rgb_param in ["custom_r", "custom_g", "custom_b"]:
            if rgb_param in self.controls:
                control = self.controls[rgb_param]
                if isinstance(control, QSlider):
                    control.setEnabled(is_custom)
                elif isinstance(control, QComboBox):
                    control.setEnabled(is_custom)
                elif isinstance(control, QHBoxLayout):
                    for widget in control.children():
                        if isinstance(widget, QSlider):
                            widget.setEnabled(is_custom)

        logging.debug(f"Finished adding controls for parameters: {list(self.controls.keys())}")

    def _add_slider_control(self, param, current_params, callback, label):
        """
        Add a slider control for numeric parameters (int or float).

        Args:
            param (dict): Parameter definition.
            current_params (dict): Current parameter values.
            callback (function): Function to call when the value changes.
            label (QLabel): The label widget for the parameter.
        """
        slider_layout = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)

        is_float = param["type"] == "float"

        # Configure slider for int or float parameters
        if is_float:
            slider.setMinimum(int(param["min"] * 10))  # Scale float for precision
            slider.setMaximum(int(param["max"] * 10))
            slider.setSingleStep(int(param.get("step", 0.1) * 10))
            value = int(current_params.get(param["name"], param["default"]) * 10)  # Convert float to int
        else:
            slider.setMinimum(param["min"])
            slider.setMaximum(param["max"])
            slider.setSingleStep(param.get("step", 1))
            value = int(current_params.get(param["name"], param["default"]))  # Ensure integer

        slider.setValue(value)

        # Label to display the current value
        value_label = QLabel(str(value / 10) if is_float else str(value))

        # Connect the slider's value change to the handler
        slider.valueChanged.connect(
            lambda val: self.on_slider_change(val, param, value_label, callback, is_float)
        )

        slider_layout.addWidget(slider)
        slider_layout.addWidget(value_label)
        self.form_layout.addRow(label, slider_layout)

        # Store control reference
        self.controls[param["name"]] = slider

    def _add_combobox_control(self, param, current_params, callback, label):
        """
        Adds a dropdown control for string parameters.

        Args:
            param (dict): Parameter definition.
            current_params (dict): Current parameter values.
            callback (function): Function to call when the selection changes.
            label (QLabel): The label widget for the parameter.
        """
        combo = QComboBox()
        combo.addItems(param["options"])

        current_value = current_params.get(param["name"], param["default"])
        index = combo.findText(current_value, Qt.MatchFixedString)
        if index >= 0:
            combo.setCurrentIndex(index)
            logging.debug(f"Set current index for {param['name']} to {index}")
        else:
            logging.warning(f"Current value '{current_value}' not found in options for {param['name']}")
            combo.setCurrentIndex(0)  # Fallback to first option

        # Disconnect any existing signals to prevent multiple connections
        try:
            combo.currentTextChanged.disconnect()
            logging.debug(f"Disconnected existing signals for combobox: {param['name']}")
        except TypeError:
            pass  # No existing connections

        def on_color_mode_change(value):
            """
            Handles changes to the color mode combobox.

            Args:
                value (str): The selected color mode.
            """
            logging.debug(f"Color mode changed to: {value}")

            # Enable or disable custom RGB sliders based on selection
            is_custom = value == "Custom"
            for rgb_param in ["custom_r", "custom_g", "custom_b"]:
                if rgb_param in self.controls:
                    control = self.controls[rgb_param]
                    if isinstance(control, QSlider):
                        control.setEnabled(is_custom)
                    elif isinstance(control, QComboBox):
                        control.setEnabled(is_custom)
                    elif isinstance(control, QHBoxLayout):
                        for widget in control.children():
                            if isinstance(widget, QSlider):
                                widget.setEnabled(is_custom)

            # Call the callback function correctly
            if callable(callback):
                callback(param["name"], value, combo)
            else:
                logging.error("Callback function is not callable")

        # ✅ Correctly connect the combobox change event to on_color_mode_change()
        combo.currentTextChanged.connect(on_color_mode_change)

        self.form_layout.addRow(label, combo)
        self.controls[param["name"]] = combo
        logging.debug(f"Added combobox control for {param['name']} with options {param['options']}")

    def _add_checkbox_control(self, param, current_params, callback, label):
        """
        Adds a checkbox control for boolean parameters.

        Args:
            param (dict): Parameter definition.
            current_params (dict): Current parameter values.
            callback (function): Function to call when the state changes.
            label (QLabel): The label widget for the parameter.
        """
        checkbox = QCheckBox()
        checkbox.setChecked(current_params.get(param["name"], param["default"]))

        # Disconnect any existing signals to prevent multiple connections
        try:
            checkbox.stateChanged.disconnect()
            logging.debug(f"Disconnected existing signals for checkbox: {param['name']}")
        except TypeError:
            pass  # No existing connections

        def on_checkbox_state_change(state):
            """
            Handles changes to the checkbox state.

            Args:
                state (int): The new state of the checkbox.
            """
            is_checked = state == Qt.Checked
            logging.debug(f"Checkbox '{param['name']}' changed to: {is_checked}")
            if callable(callback):
                callback(param["name"], is_checked, checkbox)
            else:
                logging.error("Callback function is not callable")

        checkbox.stateChanged.connect(on_checkbox_state_change)

        self.form_layout.addRow(label, checkbox)
        self.controls[param["name"]] = checkbox
        logging.debug(f"Added checkbox control for {param['name']}")

    def _add_file_picker_control(self, param, current_params, callback, label):
        """
        Add a file picker control for file path parameters.
        """
        layout = QHBoxLayout()
        editor = QLineEdit()
        # Set current or default path
        editor.setText(current_params.get(param['name'], param.get('default', '')))
        button = QPushButton("Browse")
        def on_browse():
            path, _ = QFileDialog.getOpenFileName(
                self, f"Select {param.get('label', param['name'])}", "", param.get('file_filter', 'All Files (*)')
            )
            if path:
                editor.setText(path)
                if callable(callback):
                    callback(param['name'], path, editor)
        button.clicked.connect(on_browse)
        layout.addWidget(editor)
        layout.addWidget(button)
        self.form_layout.addRow(label, layout)
        self.controls[param['name']] = editor

    def clear_layout(self):
        """
        Clears all widgets and layouts from the form layout.
        """
        logging.debug("Starting to clear the form layout.")

        while self.form_layout.count():
            item = self.form_layout.takeAt(0)

            if item is None:
                logging.warning("Encountered a NoneType item in the form layout.")
                continue  # Skip NoneType items safely

            if item.widget():
                # Handle widget items
                widget = item.widget()
                logging.debug(f"Removing widget: {widget} (Type: {type(widget)})")
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                # Handle nested layouts
                layout = item.layout()
                logging.debug(f"Clearing nested layout: {layout} (Type: {type(layout)})")
                self._clear_nested_layout(layout)
            else:
                logging.debug("Encountered an unknown item type in layout, skipping.")

        logging.debug("Finished clearing the form layout.")

    def _clear_nested_layout(self, layout):
        """
        Recursively clears a nested layout.

        Args:
            layout (QLayout): The layout to clear.
        """
        logging.debug(f"Clearing nested layout: {layout}")
        while layout.count():
            sub_item = layout.takeAt(0)

            if sub_item is None:
                logging.warning("Encountered a NoneType sub-item in nested layout.")
                continue  # Skip NoneType safely

            if sub_item.widget():
                widget = sub_item.widget()
                logging.debug(f"Removing nested widget: {widget} (Type: {type(widget)})")
                widget.setParent(None)
                widget.deleteLater()
            elif sub_item.layout():
                nested_layout = sub_item.layout()
                self._clear_nested_layout(nested_layout)

        layout.deleteLater()

    def on_slider_change(self, value, param, label_widget, callback, is_float):
        """
        Handle slider value changes and update the associated label.

        Args:
            value (int): The new slider value.
            param (dict): The parameter associated with the slider.
            label_widget (QLabel): The label to update with the slider's value.
            callback (function): The callback to invoke with the updated parameter value.
            is_float (bool): Whether the parameter is a float.
        """
        # Adjust value for float sliders
        if is_float:
            display_value = value / 10  # Convert back to float for display and callback
        else:
            display_value = value

        # Update the label with the new value
        display_text = f"{display_value:.1f}" if is_float else str(display_value)
        label_widget.setText(display_text)

        logging.debug(f"Slider for {param['name']} changed to {display_text}")

        # Call the callback with the updated value
        callback(param["name"], display_value, label_widget)
