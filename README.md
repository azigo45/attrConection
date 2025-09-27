# Attribute Connector

This repository contains a styled version of the Attribute Connector tool for Maya.

## Standalone Qt development

The script now detects whether it is running inside Maya. When the Maya Python API
is not available, lightweight stubs are used so that the UI can be launched in a
plain PySide2 / Qt environment. This makes it possible to iterate on the styling
and layout without a Maya session running.

To preview the UI outside Maya:

```bash
python attr_connector.py
```

In standalone mode the Maya-specific actions (Connect/Disconnect) are disabled
and placeholder rows are added when using the **Add to** buttons so you can
inspect the flow of the interface.
