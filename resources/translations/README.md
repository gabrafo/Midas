# Translations

This directory holds compiled `.qm` translation files loaded at runtime.

## Source language

The source strings in `qsTr()` are in **English**.
English requires no `.qm` file — it is used directly.

## Adding a new language

1. **Extract translatable strings** into a `.ts` file:

   ```bash
   pyside6-lupdate qml/**/*.qml -ts resources/translations/midas_xx.ts
   ```

2. **Translate** using Qt Linguist:

   ```bash
   pyside6-linguist resources/translations/midas_xx.ts
   ```

3. **Compile** to binary `.qm`:

   ```bash
   pyside6-lrelease resources/translations/midas_xx.ts
   ```

4. The app picks up `resources/translations/midas_<code>.qm` automatically.
   Supported codes: `br`, `es` (add more in `LanguageManager._LANGUAGES`).

## File naming

| File           | Description                              |
|----------------|------------------------------------------|
| `midas_br.qm`  | Compiled Portuguese (pt-BR) translations |
| `midas_br.ts`  | Editable Portuguese translations (XML)   |
| `midas_es.qm`  | Compiled Spanish translations            |
| `midas_es.ts`  | Editable Spanish translations (XML)      |
