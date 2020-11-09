function make_progress_bar() {
  let source = new EventSource(Url + "progress");
  source.onmessage = function (event) {
    $("#progress-bar")
      .css("width", event.data + "%")
      .attr("aria-valuenow", event.data);
    $("#progress-bar").text(event.data + "%");
    if (event.data == 100) {
      source.close();
    }
  };
}

let coefficient_chart = undefined;

function drawCoefficient(coefficients, samples) {
  const ctx = $("#coefficient-graph")[0].getContext("2d");
  const lineChartData = {
    datasets: [{ data: coefficients, borderColor: "blue", fill: false }],
    labels: [...Array(samples).keys()],
  };
  if (coefficient_chart === undefined) {
    coefficient_chart = new Chart.Line(ctx, {
      data: lineChartData,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        stacked: false,
        hover: { mode: "nearest", intersect: true },
        title: { display: true, text: "Coefficient" },
        scales: {
          yAxes: [{ type: "linear", display: true, position: "left" }],
        },
        legend: { display: false },
      },
    });
    window.myLine = coefficient_chart;
  } else {
    coefficient_chart.data = lineChartData;
    coefficient_chart.update();
  }
}

let discount_chart = undefined;

function drawDiscount(discount, samples) {
  const ctx = $("#discount-factor-graph")[0].getContext("2d");
  const lineChartData = {
    datasets: [{ data: discount, borderColor: "red", fill: false }],
    labels: [...Array(samples).keys()],
  };
  if (discount_chart === undefined) {
    discount_chart = new Chart.Line(ctx, {
      data: lineChartData,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        stacked: false,
        hover: { mode: "nearest", intersect: true },
        title: { display: true, text: "Discount Factor" },
        scales: {
          yAxes: [{ type: "linear", display: true, position: "left" }],
        },
        legend: { display: false },
      },
    });
    window.myLine = discount_chart;
  } else {
    discount_chart.data = lineChartData;
    discount_chart.update();
  }
}

const lineChartOps = {
  fill: false,
  lineTension: 0,
};

const borderColors = [
  "red",
  "green",
  "blue",
  "cyan",
  "magenta",
  "yellow",
  "black",
];

let group_budget_chart = undefined;

function drawGroup(group, Bmin, Bmax) {
  const ctx = $("#group-graph")[0].getContext("2d");
  const lineChartData = {
    datasets: group.map((x, i) => ({
      backgroundColor: borderColors[i],
      borderColor: borderColors[i],
      data: x["weight"],
      label: x["group"],
      ...lineChartOps,
    })),
    labels: [...Array(Bmax + 1 - Bmin).keys()].map((x) => x + Bmin),
  };
  if (group_budget_chart === undefined) {
    group_budget_chart = new Chart.Line(ctx, {
      data: lineChartData,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        stacked: false,
        hover: { mode: "nearest", intersect: true },
        title: { display: true, text: "Group weights various test budget" },
        scales: {
          yAxes: [{ type: "linear", display: true, position: "left" }],
        },
        legend: { display: true, labels: { boxWidth: 10, fontSize: 10 } },
      },
    });
    window.myLine = group_budget_chart;
  } else {
    group_budget_chart.data = lineChartData;
    group_budget_chart.update();
  }
}

const draw = SVG()
  .addTo("#budget-graph")
  .size(400, 400)
  .viewbox("0 0 400 400")
  .css({ "max-width": "100%", "max-height": "100%" });
let lines = new SVG.List([]);
// let texts = new SVG.List([]);
// let group_texts = new SVG.List([]);
let group_svg = new SVG.List([]);

const getAngle = (size, r, i) => [
  200 + r * Math.cos(Math.PI / 2 + (2 * Math.PI * i) / size),
  200 + r * Math.sin(Math.PI / 2 + (2 * Math.PI * i) / size),
];

function drawPeople(graph, group_list) {
  let len1 = Object.keys(graph).length;
  let len2 = group_list.length;
  const graph_angle = (r, i) => getAngle(len1, r, i);
  const group_angle = (r, i) => getAngle(len2, r, i);
  draw.clear();
  let g = draw.group();
  Object.entries(graph).forEach((el, i) =>
    el[1].forEach((k) => {
      lines.push(
        g
          .line(
            ...graph_angle(150, i),
            ...group_angle(40, group_list.indexOf(k))
          )
          .stroke({ color: "#888", width: 1 })
          .data("name", el[0])
      );
    })
  );
  Object.keys(graph).forEach((el, i) => {
    // texts.push(
    //   g
    //     .text(`${el.slice(10)}`)
    //     .move(...graph_angle(150, i))
    //     .font({
    //       family: "Helvetica",
    //       size: 8,
    //       anchor: i > len1 / 2 ? "start" : "end",
    //     })
    //     .hide()
    // );
    g.circle(8)
      .fill("blue")
      .translate(-4, -4)
      .move(...graph_angle(150, i))
      .on("mouseover", function () {
        $("#selected-name").text(el.split("_").slice(-2)[0]);
        // texts[i].show();
      });
    // .on("mouseout", function () {
    //   texts[i].hide();
    // });
  });
  group_list.forEach((el, j) => {
    // group_texts.push(
    //   g
    //     .text(`${el}`)
    //     .move(...group_angle(42, j))
    //     .font({
    //       family: "Helvetica",
    //       size: 8,
    //       anchor: j > len2 / 2 ? "start" : "end",
    //     })
    //     .hide()
    // );
    group_svg.push(
      g
        .circle(10)
        .fill("green")
        .translate(-5, -5)
        .move(...group_angle(40, j))
        .data("name", el)
        .on("mouseover", function () {
          $("#selected-name").text(el);
          // group_texts[j].show();
        })
      // .on("mouseout", function () {
      //   $("#selected-name").text("");
      //   group_texts[j].hide();
      // })
    );
  });
}

function highlightGraph(people, group) {
  lines.stroke({ color: "#888", width: 1 });
  group_svg.fill("green");
  lines.each((item) => {
    if (people.includes(item.data("name")))
      return item.stroke({ color: "#FF0000", width: 2 });
    return item;
  });
  group_svg.each((item) => {
    if (group.includes(item.data("name"))) return item.fill("#FF0000");
    return item;
  });
}

function drawList(people, group) {
  let people_lst = $("#people-list");
  people_lst.children().not(":first").remove();
  people.forEach((el) =>
    people_lst.append(
      `<li class="list-group-item break-word list-text p-1">${el}</li>`
    )
  );
  let group_lst = $("#groups-list");
  group_lst.children().not(":first").remove();
  group.forEach((el) =>
    group_lst.append(
      `<li class="list-group-item break-word list-text p-1">${el}</li>`
    )
  );
}
