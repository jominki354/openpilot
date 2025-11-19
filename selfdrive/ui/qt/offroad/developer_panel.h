#pragma once

#include <QTimer>
#include "selfdrive/ui/qt/offroad/settings.h"

class DeveloperPanel : public ListWidget {
  Q_OBJECT
public:
  explicit DeveloperPanel(SettingsWindow *parent);
  void showEvent(QShowEvent *event) override;

private:
  Params params;
  ParamControl* adbToggle;
  ParamControl* joystickToggle;
  ParamControl* joystickSmoothingToggle;
  ParamControl* longManeuverToggle;
  ParamControl* experimentalLongitudinalToggle;
  ButtonControl* presetDefault;
  ButtonControl* presetSoft;
  ButtonControl* presetNormal;
  ButtonControl* presetSport;
  CValueControl* steeringSensitivity;
  CValueControl* steeringGain;
  CValueControl* accelSensitivity;
  CValueControl* accelGain;
  CValueControl* deadzoneControl;
  CValueControl* maxSpeedControl;
  bool is_release;
  bool offroad = false;

private slots:
  void updateToggles(bool _offroad);
  void updatePresetButtons();
  void updateValueControls();
};
