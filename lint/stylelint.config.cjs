// Example for an app that already uses stylelint.
// CI in this repository runs script/rtl_lint.py, which checks the same idea
// without an npm install: physical left/right properties and Hebrew tracking.
// A third-party widget can opt out of script/rtl_lint.py with rtl-lint-disable-line.
// For this config, use stylelint-disable-next-line property-disallowed-list.
// letter-spacing above 0.02em is checked by script/rtl_lint.py.

module.exports = {
  rules: {
    "property-disallowed-list": [
      "margin-left",
      "margin-right",
      "padding-left",
      "padding-right",
      "border-left",
      "border-right",
      "left",
      "right",
      "scroll-margin-left",
      "scroll-margin-right",
      "scroll-padding-left",
      "scroll-padding-right",
    ],
    "declaration-property-value-disallowed-list": {
      "text-align": ["left", "right"],
      "float": ["left", "right"],
      "clear": ["left", "right"],
    },
  },
};
