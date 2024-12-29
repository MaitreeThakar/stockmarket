var stock_called = {}
var intervals = {}
function get_data(callback, symbol){
    $.ajax({
        type:"GET", 
        data:{"symbol": symbol, 'changed':'true'},
        success: function(response){
            data = response.data
            symbol_name = response.name
            if (callback){
                callback(data, symbol_name);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR)
            console.log(textStatus)
            console.log(errorThrown)
        }
    });
}

function handle_callback(plot_name, symbol){
    let intervalId;
    get_data(function callback(data, symbol_name){
        plot_chart(data, plot_name, symbol_name)
        intervalId = setInterval(() => {
            updateChart(changed, plot_name, symbol, intervalId);
        }, 5000);
        for (var key in intervals){
            if (key == symbol){
                clearInterval(intervals[key])
            }
        }
        intervals[symbol] = intervalId;

    }, symbol)
}

// var stock1Called = false
// var stock2Called = false

stock_called = {
    'stock1Called':false,
    'stock2Called':false
}

const stock1Button = document.getElementById('reliance-tab')
stock1Button.addEventListener('click', plot_stock1)
function plot_stock1(){
    if (stock_called.stock1Called == false){
        handle_callback('stock1-graph', 'reliance');
        stock_called.stock1Called = true
    }
}

const stock2Button = document.getElementById('hdfc-tab')
stock2Button.addEventListener('click', plot_stock2);
function plot_stock2() {
    if (stock_called.stock2Called == false){
        handle_callback('stock2-graph', 'hdfc');
        stock_called.stock2Called = true
    }
}
