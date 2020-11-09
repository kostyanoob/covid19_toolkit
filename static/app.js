const Url = "http://127.0.0.1:5000/";
let solution = [];

$(document).ready(function () {
  d = new Date();
  $("#currentDate").val(d.toISOString().substr(0, 10));
   d.setDate(d.getDate() - 1);
   $("#previousDate").val(d.toISOString().substr(0, 10));
});

$("#spreadsheet").submit(function (e) {
  e.preventDefault();
  let currentDate = $("#currentDate").val();
  let previousDate = $("#previousDate").val();
  $.get(Url + "spreadsheet", { currentDate, previousDate }, (data) => {
    $("#spreadsheet-result").text(data["message"]);
    if (data["state"] == true) {
      $("#spreadsheet-btn").prop("disabled", true);
      $("#date-selector").removeClass("col-md-12").addClass("col-md-6");
      $("#solver").toggle();
      makeYAML_list();
    } else {
      console.log(data["error"]);
    }
  });
});

// Risk Editor

function makeYAML_list(config_path) {
  $.get(Url + "model_list", (data) => {
    $(".model-select").empty();
    data["list"].forEach((el, i) => {
      $("#model-select-1, #model-select-2").append(
        `<option value=${el}>${el}</option>`
      );
    });
    if (config_path) $("#model-select-1, #model-select-2").val(config_path);
  });
}

$("#risk-editor-btn").click(function () {
  makeRiskEditor(true);
  $("#risk-editor").modal();
});

function makeRiskEditor(editing) {
  $("#coefficient").prop(
    "disabled",
    $("#coefficient-select").val() !== "Custom"
  );
  let coefficient_kind = $("#coefficient-select").val();
  let coefficient_val = $("#coefficient").val();
  let coefficient_samples = $("#sampling-coefficient").val();
  let discount_factor_kind = $("#discount-factor-select").val();
  let discount_factor_val = $("#discount-factor").val();
  let discount_factor_samples = $("#sampling-discount-factor").val();
  let path = $("#model-select-1").val();
  $.get(
    Url + "risk_model",
    {
      ...(editing
        ? { path }
        : {
            coefficients: {
              risk_factor_coeff_kind: String(coefficient_kind).toLowerCase(),
              arg: coefficient_val,
            },
            discount_factor: {
              risk_factor_discount_kind: String(
                discount_factor_kind
              ).toLowerCase(),
              arg: discount_factor_val,
            },
          }),
      coefficient_samples,
      discount_factor_samples,
    },
    (data) => {
      if (data["state"] === true) {
        drawCoefficient(data["coefficients"], +coefficient_samples);
        drawDiscount(data["discount_factor"], +discount_factor_samples);
        $("#coefficient-select").val(data["coeff_kind"]);
        $("#coefficient").prop("disabled", data["coeff_kind"] !== "custom");
        $("#coefficient").val(data["coeff_vector"]);
        $("#discount-factor-select").val(data["discount_kind"]);
        $("#discount-factor").val(data["discount_vector"]);
      } else {
        console.log(data["error"]);
      }
    }
  );
}

$("#model-select-1").change(function () {
  $("#model-select-2").val($("#model-select-1").val());
});

$("#model-select-2").change(function () {
  $("#model-select-1").val($("#model-select-2").val());
  makeRiskEditor(true);
});

$(".risk-editor-data").change(function () {
  makeRiskEditor(false);
});

$("#new-yaml-btn, #old-yaml-btn").click(function () {
  $("#model-form-inline").toggle();
  $("#new-yaml-form").toggle();
});

$("#save-select-btn").click(function () {
  let config_path = $("#new-yaml-file").val() + ".yaml";
  $.get(Url + "save_model", { config_path }, (data) => {
    if (data["state"] === true) {
      makeYAML_list(config_path);
    } else {
      console.log(data["error"]);
    }
  });
});

$("#risk-model").submit(function (e) {
  e.preventDefault();
  $("#model-btn").prop("disabled", true);
  $("#explore-btn").prop("disabled", true);
  let Bmin = +$("#minimumBudget").val();
  let Bmax = +$("#maximumBudget").val();
  let ratio = +$("#g2f-ratio").val();
  let model_path = $("#model-select-1").val();

  $("#solve-result").text("Solving...");
  $("#progress-bar")
    .toggleClass("progress-bar-animated")
    .toggleClass("bg-success");
  $(".progress").show();
  make_progress_bar();

  $.get(Url + "solve", { Bmin, Bmax, ratio, model_path }, (data) => {
    $("#solve-result").text(data["message"]);
    if (data["state"] === true) {
      solution = data["response"];
      makeBudget(Bmin, Bmax);
      $("#explore-btn").toggle();
      $("#spreadsheet-btn").prop("disabled", false);
      $("#model-btn").text("Solve again");
      $("#modal-page").modal();
    } else {
      console.log(data["error"]);
    }
    $("#progress-bar")
      .toggleClass("progress-bar-animated")
      .toggleClass("bg-success");
  });

  $("#explore-btn").prop("disabled", false);
  $("#model-btn").prop("disabled", false);
});

// Budget Explorer

function makeBudget(Bmin, Bmax) {
  let currDate = $("#currentDate").val();
  let Binitial = Math.floor((Bmin + Bmax) / 2);
  $("#budget-title").text(`Budget Explorer (${currDate})`);
  $("#budget-range").prop("min", Bmin);
  $("#budget-range").prop("max", Bmax);
  $("#budget-range").prop("value", Binitial);
  $("label[for='budget-range']").text("Budget = " + Binitial);
  $("#budget-btn").text("Produce checklist for budget B = " + Binitial);
  // $("#group-graph").prop(
  //   "src",
  //   `../Figures/${currDate}/Group_weight_B_${Bmin}-${Bmax}.png`
  // );
  // $("#budget-graph").prop(
  //   "src",
  //   `../Figures/${currDate}/Graph_B_${Binitial}.png`
  // );

  $.get(Url + "institution", {}, (data) => {
    if (data["state"]) {
      const response = data["response"];
      drawGroup(response["group"], Bmin, Bmax);
      drawPeople(
        response["graph"],
        response["group"].map((x) => x["group"])
      );
      makeBudgetExplorer(Binitial);
    } else {
      console.log(data["error"]);
    }
  });
}

$("#explore-btn").click(function () {
  $("#modal-page").modal();
});

$("#budget-range").on("input", function () {
  let budget = $("#budget-range").val();
  $("label[for='budget-range']").text("Budget = " + budget);
  makeBudgetExplorer(budget);

  $("#budget-btn").text("Produce checklist for budget B = " + budget);
  // $("#budget-graph").prop(
  //   "src",
  //   `../Figures/${currDate}/Graph_B_${budget}.png`
  // );
});

function makeBudgetExplorer(budget) {
  drawList(...solution[budget]);
  highlightGraph(...solution[budget]);
}

$("#budget-btn").click(function () {
  let budget = $("#budget-range").val();
  $.get(Url + "checklist", { budget }, (data) => {
    $("#checklist-result").text(data["message"]);
    if (data["state"] !== true) {
      console.log(data["error"]);
    }
  });
});
