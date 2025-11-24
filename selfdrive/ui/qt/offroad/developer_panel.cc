#include "selfdrive/ui/qt/offroad/developer_panel.h"
#include "selfdrive/ui/qt/widgets/ssh_keys.h"
#include "selfdrive/ui/qt/widgets/controls.h"

DeveloperPanel::DeveloperPanel(SettingsWindow *parent) : ListWidget(parent) {
  adbToggle = new ParamControl("AdbEnabled", tr("Enable ADB"),
            tr("ADB (Android Debug Bridge) allows connecting to your device over USB or over the network. See https://docs.comma.ai/how-to/connect-to-comma for more info."), "");
  addItem(adbToggle);

  // SSH keys
  addItem(new SshToggle());
  addItem(new SshControl());

  joystickToggle = new ParamControl("JoystickDebugMode", tr("조이스틱 모드"), "", "");
  QObject::connect(joystickToggle, &ParamControl::toggleFlipped, [=](bool state) {
    params.putBool("LongitudinalManeuverMode", false);
    longManeuverToggle->refresh();
  });
  addItem(joystickToggle);

  // Joystick Smoothing Toggle
  joystickSmoothingToggle = new ParamControl("JoystickSmoothingEnabled",
                                              tr("조이스틱 민감도"),
                                              tr("부드러운 조작을 위한 필터링 적용"), "");
  addItem(joystickSmoothingToggle);

  // Joystick Preset Buttons (using ButtonControl like openpilot style)
  presetDefault = new ButtonControl(tr("프리셋: 기본값"), tr("적용"),
                                     tr("100, 100, 100, 100, 0"));
  connect(presetDefault, &ButtonControl::clicked, [=]() {
    params.put("JoystickSteeringSensitivity", "100");
    params.put("JoystickSteeringGain", "100");
    params.put("JoystickAccelSensitivity", "100");
    params.put("JoystickAccelGain", "100");
    params.put("JoystickDeadzone", "0");
    params.put("JoystickPreset", "기본값");
    updatePresetButtons();
    updateValueControls();
  });
  addItem(presetDefault);

  presetSoft = new ButtonControl(tr("프리셋: 부드럽게"), tr("적용"),
                                  tr("20, 60, 20, 60, 12"));
  connect(presetSoft, &ButtonControl::clicked, [=]() {
    params.put("JoystickSteeringSensitivity", "20");
    params.put("JoystickSteeringGain", "60");
    params.put("JoystickAccelSensitivity", "20");
    params.put("JoystickAccelGain", "60");
    params.put("JoystickDeadzone", "12");
    params.put("JoystickPreset", "부드럽게");
    updatePresetButtons();
    updateValueControls();
  });
  addItem(presetSoft);

  presetNormal = new ButtonControl(tr("프리셋: 보통"), tr("적용"),
                                    tr("60, 120, 60, 120, 5"));
  connect(presetNormal, &ButtonControl::clicked, [=]() {
    params.put("JoystickSteeringSensitivity", "60");
    params.put("JoystickSteeringGain", "120");
    params.put("JoystickAccelSensitivity", "60");
    params.put("JoystickAccelGain", "120");
    params.put("JoystickDeadzone", "5");
    params.put("JoystickPreset", "보통");
    updatePresetButtons();
    updateValueControls();
  });
  addItem(presetNormal);

  presetSport = new ButtonControl(tr("프리셋: 강하게"), tr("적용"),
                                   tr("95, 180, 95, 180, 2"));
  connect(presetSport, &ButtonControl::clicked, [=]() {
    params.put("JoystickSteeringSensitivity", "95");
    params.put("JoystickSteeringGain", "180");
    params.put("JoystickAccelSensitivity", "95");
    params.put("JoystickAccelGain", "180");
    params.put("JoystickDeadzone", "2");
    params.put("JoystickPreset", "강하게");
    updatePresetButtons();
    updateValueControls();
  });
  addItem(presetSport);

  // Steering Sensitivity (Speed)
  steeringSensitivity = new CValueControl("JoystickSteeringSensitivity",
                                           tr("  조향 반응 속도"),
                                           tr("100=즉시반응(기본값), 10~99=부드럽게"),
                                           10, 100, 10);
  addItem(steeringSensitivity);

  // Steering Gain (Strength)
  steeringGain = new CValueControl("JoystickSteeringGain",
                                    tr("  조향 반응 강도"),
                                    tr("100=기본값, 50~99=약하게, 101~400=강하게"),
                                    50, 400, 10);
  addItem(steeringGain);

  // Accel Sensitivity (Speed)
  accelSensitivity = new CValueControl("JoystickAccelSensitivity",
                                        tr("  액셀 반응 속도"),
                                        tr("100=즉시반응(기본값), 10~99=부드럽게"),
                                        10, 100, 10);
  addItem(accelSensitivity);

  // Accel Gain (Strength)
  accelGain = new CValueControl("JoystickAccelGain",
                                 tr("  액셀 반응 강도"),
                                 tr("100=기본값, 50~99=약하게, 101~400=강하게"),
                                 50, 400, 10);
  addItem(accelGain);

  // Deadzone
  deadzoneControl = new CValueControl("JoystickDeadzone",
                                       tr("  입력 무시 범위"),
                                       tr("0=비활성화(기본값), 1~20=활성화"),
                                       0, 20, 1);
  addItem(deadzoneControl);

  // Joystick Max Speed
  maxSpeedControl = new CValueControl("JoystickMaxSpeed",
                                       tr("  최대 속도 제한"),
                                       tr("0=제한없음(기본값), 1~250=속도제한(km/h)"),
                                       0, 250, 5);
  addItem(maxSpeedControl);

  // Show/hide detail controls based on smoothing toggle
  QObject::connect(joystickSmoothingToggle, &ParamControl::toggleFlipped, [=](bool enabled) {
    presetDefault->setVisible(enabled);
    presetSoft->setVisible(enabled);
    presetNormal->setVisible(enabled);
    presetSport->setVisible(enabled);
    steeringSensitivity->setVisible(enabled);
    steeringGain->setVisible(enabled);
    accelSensitivity->setVisible(enabled);
    accelGain->setVisible(enabled);
    deadzoneControl->setVisible(enabled);
    // maxSpeedControl->setVisible(enabled); // Always show max speed control
  });

  // Set initial visibility
  bool smoothingEnabled = params.getBool("JoystickSmoothingEnabled");
  presetDefault->setVisible(smoothingEnabled);
  presetSoft->setVisible(smoothingEnabled);
  presetNormal->setVisible(smoothingEnabled);
  presetSport->setVisible(smoothingEnabled);
  steeringSensitivity->setVisible(smoothingEnabled);
  steeringGain->setVisible(smoothingEnabled);
  accelSensitivity->setVisible(smoothingEnabled);
  accelGain->setVisible(smoothingEnabled);
  deadzoneControl->setVisible(smoothingEnabled);
  maxSpeedControl->setVisible(true); // Always show max speed control

  // Initialize default values if not set
  if (params.get("JoystickSteeringSensitivity").empty()) {
    params.put("JoystickSteeringSensitivity", "100");
  }
  if (params.get("JoystickSteeringGain").empty()) {
    params.put("JoystickSteeringGain", "100");
  }
  if (params.get("JoystickAccelSensitivity").empty()) {
    params.put("JoystickAccelSensitivity", "100");
  }
  if (params.get("JoystickAccelGain").empty()) {
    params.put("JoystickAccelGain", "100");
  }
  if (params.get("JoystickDeadzone").empty()) {
    params.put("JoystickDeadzone", "0");
  }
  if (params.get("JoystickPreset").empty()) {
    params.put("JoystickPreset", "기본값");
  }
  if (params.get("JoystickMaxSpeed").empty()) {
    params.put("JoystickMaxSpeed", "0");
  }

  longManeuverToggle = new ParamControl("LongitudinalManeuverMode", tr("Longitudinal Maneuver Mode"), "", "");
  QObject::connect(longManeuverToggle, &ParamControl::toggleFlipped, [=](bool state) {
    params.putBool("JoystickDebugMode", false);
    joystickToggle->refresh();
  });
  addItem(longManeuverToggle);

  experimentalLongitudinalToggle = new ParamControl(
    "AlphaLongitudinalEnabled",
    tr("openpilot Longitudinal Control (Alpha)"),
    QString("<b>%1</b><br><br>%2")
      .arg(tr("WARNING: openpilot longitudinal control is in alpha for this car and will disable Automatic Emergency Braking (AEB)."))
      .arg(tr("On this car, openpilot defaults to the car's built-in ACC instead of openpilot's longitudinal control. "
              "Enable this to switch to openpilot longitudinal control. Enabling Experimental mode is recommended when enabling openpilot longitudinal control alpha.")),
    ""
  );
  experimentalLongitudinalToggle->setConfirmation(true, false);
  QObject::connect(experimentalLongitudinalToggle, &ParamControl::toggleFlipped, [=]() {
    updateToggles(offroad);
  });
  addItem(experimentalLongitudinalToggle);

  // Joystick and longitudinal maneuvers should be hidden on release branches
  is_release = params.getBool("IsReleaseBranch");

  // Toggles should be not available to change in onroad state
  QObject::connect(uiState(), &UIState::offroadTransition, this, &DeveloperPanel::updateToggles);

  // Set initial preset button colors
  updatePresetButtons();
}

void DeveloperPanel::updatePresetButtons() {
  std::string preset = params.get("JoystickPreset");

  const QString activeStyle = R"(
    QPushButton {
      background-color: #33Ab4C;
      color: white;
      border-radius: 30px;
      font-weight: bold;
    }
  )";

  const QString normalStyle = R"(
    QPushButton {
      background-color: #393939;
      color: #E4E4E4;
      border-radius: 30px;
    }
  )";

  // Reset all buttons to normal style
  presetDefault->setStyleSheet(normalStyle);
  presetSoft->setStyleSheet(normalStyle);
  presetNormal->setStyleSheet(normalStyle);
  presetSport->setStyleSheet(normalStyle);

  // Highlight active preset
  if (preset == "기본값") {
    presetDefault->setStyleSheet(activeStyle);
  } else if (preset == "부드럽게") {
    presetSoft->setStyleSheet(activeStyle);
  } else if (preset == "보통") {
    presetNormal->setStyleSheet(activeStyle);
  } else if (preset == "강하게") {
    presetSport->setStyleSheet(activeStyle);
  }
}

void DeveloperPanel::updateValueControls() {
  // Force UI update by hiding and showing
  steeringSensitivity->hide();
  steeringGain->hide();
  accelSensitivity->hide();
  accelGain->hide();
  deadzoneControl->hide();
  maxSpeedControl->hide();

  steeringSensitivity->show();
  steeringGain->show();
  accelSensitivity->show();
  accelGain->show();
  deadzoneControl->show();
  maxSpeedControl->show();
}

void DeveloperPanel::updateToggles(bool _offroad) {
  for (auto btn : findChildren<ParamControl *>()) {
    btn->setVisible(!is_release);

    /*
     * experimentalLongitudinalToggle should be toggelable when:
     * - visible, and
     * - during onroad & offroad states
     */
    if (btn != experimentalLongitudinalToggle) {
      btn->setEnabled(true);  // fix.. allow toggle anytime
    }
  }

  // longManeuverToggle and experimentalLongitudinalToggle should not be toggleable if the car does not have longitudinal control
  auto cp_bytes = params.get("CarParamsPersistent");
  if (!cp_bytes.empty()) {
    AlignedBuffer aligned_buf;
    capnp::FlatArrayMessageReader cmsg(aligned_buf.align(cp_bytes.data(), cp_bytes.size()));
    cereal::CarParams::Reader CP = cmsg.getRoot<cereal::CarParams>();

    if (!CP.getAlphaLongitudinalAvailable() || is_release) {
      params.remove("AlphaLongitudinalEnabled");
      experimentalLongitudinalToggle->setEnabled(false);
    }

    /*
     * experimentalLongitudinalToggle should be visible when:
     * - is not a release branch, and
     * - the car supports experimental longitudinal control (alpha)
     */
    experimentalLongitudinalToggle->setVisible(CP.getAlphaLongitudinalAvailable() && !is_release);

    longManeuverToggle->setEnabled(hasLongitudinalControl(CP) && _offroad);
  } else {
    longManeuverToggle->setEnabled(false);
    experimentalLongitudinalToggle->setVisible(false);
  }
  experimentalLongitudinalToggle->refresh();

  offroad = _offroad;
}

void DeveloperPanel::showEvent(QShowEvent *event) {
  updateToggles(offroad);
}


