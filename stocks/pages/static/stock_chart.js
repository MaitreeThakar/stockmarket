// -------------------------- plot chart ------------------------------
function plot_chart(data, plot_name = "plot", symbol_name = "reliance") {
  // console.log("inside plot chart ----------------------------");
  // console.log(data);

  // console.log("end ------------------------------------");
  var y = data.y;
  var consecutiveUpIndices = [];
  var consecutiveDownIndices = [];
  for (var i = 11; i < y.length; i++) {
    var previousTenValues = y.slice(i - 9, i + 1);
    var isIncreasing = true;
    var isDecreasing = true;
    for (var j = 1; j < previousTenValues.length; j++) {
      if (previousTenValues[j] < previousTenValues[j - 1]) {
        isIncreasing = false;
      }
      if (previousTenValues[j] > previousTenValues[j - 1]) {
        isDecreasing = false;
      }
    }
    if (isIncreasing) {
      consecutiveUpIndices.push(i);
    } else if (isDecreasing) {
      consecutiveDownIndices.push(i);
    }
    var highlightUpPoints = {
      x: [],
      y: [],
      mode: "markers",
      marker: {
        color: "rgba(255, 0, 0, 0.7)",
        size: 8,
      },
      name: "Up Points",
    };

    var highlightDownPoints = {
      x: [],
      y: [],
      mode: "markers",
      marker: {
        color: "rgba(0, 0, 255, 0.7)",
        size: 8,
      },
      name: "Down Points",
    };

    consecutiveUpIndices.forEach(function (index) {
      highlightUpPoints.x.push(data.x[index]);
      highlightUpPoints.y.push(data.y[index]);
    });

    consecutiveDownIndices.forEach(function (index) {
      highlightDownPoints.x.push(data.x[index]);
      highlightDownPoints.y.push(data.y[index]);
    });
  }

  var trace1 = {
    // lower band
    x: data.x,
    y: data.indicators.bollinger_bands.lower_band,
    opacity: 0,
    name: "lower band",
    customdata: [],
  };
  var trace2 = {
    // Filled Area
    x: data.x,
    y: data.indicators.bollinger_bands.ma,
    fill: "tonexty",
    opacity: 0.7,
    name: "filler",
    customdata: [],
  };

  var trace3 = {
    // Upper band (trace index 2)
    x: data.x,
    y: data.indicators.bollinger_bands.upper_band,
    fill: "tonexty",
    name: "upper band",
    customdata: [],
  };

  var trace4 = {
    x: data.x,
    y: data.y,
    name: "Current Price",
    line: {
      color: "rgb(128, 0, 128)",
      width: 1,
    },
    mode: "line",
    customdata: data.customdata,
    hovertemplate: "",
    // "Closing Price: %{customdata[0]}<br>"+
    // "Current Price: %{y}<br>"+
    // "Opening Price: %{customdata[0]}<br>"+
    // "High: %{customdata[1]}<br>"+
    // "Low: %{customdata[2]}",
  };
  var trace5 = {
    x: data.x,
    y: data.avg,
    name: "Average",
    line: {
      color: "rgb(0, 83, 138)",
      width: 1,
    },
    customdata: [],
  };
  var trace6 = {
    x: data.x,
    y: data.run_avg,
    name: "Running average",
    line: {
      color: "rgb(237, 129, 14)",
      width: 1,
    },
    customdata: [],
  };
  var trace7 = {
    x: data.x,
    y: data.volume,
    name: "Volume",
    line: {
      color: "rgb(214, 79, 0)",
      width: 2,
    },
    customdata: [],
  };

  let layout = {
    title: symbol_name,
    showlegend: true,
    xaxis: {
      title: "Time",
      tickangle: 45,
    },
    yaxis: {
      title: "Stock Price",
      tickangle: 45,
    },
  };
  let config = {
    responsive: true,
  };
  // console.log(selectedOptions);
  var traces = [];
  for (var i = 0; i < selectedOptions.length; i++) {
    switch (selectedOptions[i]) {
      case "volume":
        traces.push(trace7);
        break;
      case "upDown":
        traces.push(highlightUpPoints, highlightDownPoints);
        break;
      case "bollinger":
        traces.push(trace1, trace2, trace3);
        break;
      default:
        traces.push(trace4, trace5, trace6);
        break;
    }
  }
  console.log(traces);
  if (selectedOptions.length == 0) {
    traces.push(trace4, trace5, trace6);
  }
  // console.log("==============traces==========");
  // console.log(traces);

  Plotly.newPlot(plot_name, traces, layout, config);
}

var count = 0;
var arr_1min = [];
var historical_data = [];
var vol = [];
var lower_points = [];
var upper_points = [];
// ---------------------- update chart ------------------------
function updateChart(
  changed = false,
  plot_name = "plot",
  symbol = "reliance",
  intervalId
) {
  var buyButton = document.getElementById("buyButton");
  buyButton.addEventListener("click", function () {
    var url = buyButton.getAttribute("data-url");
    window.location.href = url;
  });

  var sellButton = document.getElementById("sellButton");
  sellButton.addEventListener("click", function () {
    var url = sellButton.getAttribute("data-url");
    window.location.href = url;
  });
  // var symbol = $('#my_dropdown').find(":selected").val()
  // console.log("inside update chart");
  changed = false;
  console.log("Values: " + changed + " " + plot_name + " " + symbol);

  $.ajax({
    // url: "/stocks/",
    type: "GET",
    data: { symbol: symbol, changed: changed },
    success: function (response) {
      if (changed == false) {
        // ========================= single update =============================
        data = response.data;
        x = data.x;
        y = data.y;
        avg = data.avg;
        run_avg = data.run_avg;
        customdata = data.customdata;
        indicators = data.indicators;
        buy_or_sell = data.buy_or_sell;
        ma = indicators.bollinger_bands.ma;
        lower_band = indicators.bollinger_bands.lower_band;
        upper_band = indicators.bollinger_bands.upper_band;

        action = buy_or_sell.action;
        volume = data.volume;

        avg_buy = buy_or_sell.avg_buy;
        avg_sell = buy_or_sell.avg_sell;
        rbq = buy_or_sell.rbq;

        sessionStorage.setItem(
          "Details",
          JSON.stringify({
            current_price: y,
            avg_buy: avg_buy,
            avg_sell: avg_sell,
            rbq: rbq,
            total_bq: 1,
            total_sq: 1,
            strength: 1,
            symbol: symbol,
          })
        );

        // if (action == 'buy' || action == 'sell'){
        //   Plotly.addTraces(plot_name, {
        //     showlegend: false,
        //     x: [x],
        //     y: [y],
        //     customdata: [[action, avg_buy, avg_sell, rbq]],
        //     mode: 'markers',
        //     marker: {
        //       color: 'red',
        //       size:10
        //     },
        //     hovertemplate: "Action: %{customdata[0]}<br>"+
        //       "Average_buy: %{customdata[1]}<br>" +
        //       "Average_sell: %{customdata[2]}<br>" +
        //       "RBQ: %{customdata[3]}<br>"
        //   })
        // }
        // --------------------------------------

        var traces = [];
        var x_list = [],
          y_list = [],
          customdata_list = [];
        var i = 0;
        for (var i = 0; i < selectedOptions.length; i++) {
          switch (selectedOptions[i]) {
            case "volume":
              x_list.push([x]);
              y_list.push([volume]);
              if (selectedOptions.length == 1) {
                traces.push(i++);
              } else {
                traces.push(i++);
              }
              customdata_list.push([null]);
              break;
            case "upDown":
              if (count === 0) {
                arr_1min = [];
              }
              count++;
              // console.log(count);
              arr_1min.push(y);
              // console.log(arr_1min);

              function avg(arr) {
                var sum = 0;
                arr.forEach(function (item, idx) {
                  sum += item;
                });
                return sum / arr.length;
              }
              if (count === 12) {
                // Check if 1 minute has passed (12 intervals of 5 seconds)
                // console.log("1 min completed");
                //count = 0;
                // // console.log('Average - ', avg(arr_1min));
                historical_data.push(avg(arr_1min));
                arr_1min = [];
                var previousTenValues = historical_data.slice(-10); // Get the previous 10 values
                //// console.log('Previous 10 values - ', previousTenValues);
                var isIncreasing = true;
                var isDecreasing = true;
                var consecutiveUpIndices = [];
                var consecutiveDownIndices = [];

                // console.log(previousTenValues);
                // console.log(y);
                for (var j = 1; j < previousTenValues.length; j++) {
                  if (previousTenValues[j] < previousTenValues[j - 1]) {
                    isIncreasing = false;
                  }
                  if (previousTenValues[j] > previousTenValues[j - 1]) {
                    isDecreasing = false;
                  }
                }

                if (isIncreasing) {
                  marker_color = "rgba(255, 0, 0, 0.7)";
                  buySelected = true;
                  consecutiveUpIndices.push(j);
                  // console.log('10 increasing points');
                } else if (isDecreasing) {
                  marker_color = "rgba(0, 0, 255, 0.7)";
                  sellSelected = true;
                  consecutiveDownIndices.push(j);
                  // console.log('10 decreasing points');
                } else {
                  // console.log('Mixed');
                  holdSelected = true;
                }

                color1 = marker_color;
              } else {
                // console.log('Up down - 1 minute not completed');
                holdSelected = true;
                color1 = "purple";
              }

              if (
                count === 12 &&
                (color1 == "rgba(255, 0, 0, 0.7)" ||
                  color1 == "rgba(0, 0, 255, 0.7)")
              ) {
                var lastPoint = {
                  x: [x],
                  y: [y],
                  mode: "markers",
                  marker: {
                    size: 8,
                    color: color1,
                  },
                  showlegend: false,
                };
                Plotly.addTraces(plot_name, lastPoint);
              }

              if (count === 12) {
                count = 0;
              }
              holdSelected = true;
              break;

            case "bollinger":
              x_list.push([x], [x], [x]);
              y_list.push([lower_band], [ma], [upper_band]);
              traces.push(i, i + 1, i + 2);
              i = i + 3;
              customdata_list.push([null], [null], [null]);
              break;
            default:
              x_list.push([x], [x], [x]);
              y_list.push([y], [avg], [run_avg]);
              traces.push(i, i + 1, i + 2);
              i = i + 3;
              customdata_list.push([customdata], [null], [null]);
              break;
          }
        }
        if (selectedOptions.length == 0) {
          x_list.push([x], [x], [x]);
          y_list.push([y], [avg], [run_avg]);
          traces.push(0, 1, 2);
          customdata_list.push([customdata], [null], [null]);
        }
        let update = {
          x: x_list,
          y: y_list,
          customdata: customdata_list,
        };
        // let update = {
        //   x: [[x], [x], [x]],
        //   y: [[y], [avg], [run_avg]],
        //   customdata: [[null], [null], [null]],
        // };
        // console.log('==============update=========')
        // console.log(update)

        // console.log("==============traces==========");
        // console.log(traces);

        Plotly.extendTraces(plot_name, update, traces);

        // -----------------------------------
        // let update = {
        //   x: [[x], [x], [x], [x], [x], [x]],
        //   y: [[lower_band], [ma], [upper_band], [y], [avg], [run_avg]],
        //   customdata: [[null], [null], [null], [customdata], [null], [null]],
        // };

        // Plotly.extendTraces(plot_name, update, [0,1,2,3,4,5]);    // all traces are selected
      } else {
        console.log("full plot");
        console.log(response);
        // for (var i=0; i< selectedOptions.length; i++){
        //   if (selectedOptions[i] == 'volume'){

        //   }
        // }
      }
    },
    error: function (jqXHR, textStatus, errorThrown) {
      console.log("AJAX error: ", textStatus, errorThrown);
      if (jqXHR.status >= 500) {
        console.error("Server error: ", jqXHR.responseText);
        console.log("API call failed. Please try again.");
      } else if (jqXHR.status >= 400) {
        console.error("Client Error: ", jqXHR.responseText);
        console.log("Unexpected data format received from the API.");
      } else {
        console.error("Unknown error:", jqXHR.status, jqXHR.responseText);
        console.log("An unknown error occurred.");
      }

      clearInterval(intervalId);
    },
  });
}
