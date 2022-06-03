/* JS code for ip.html (detail of IP address) */

function category2color(cat, alpha=1.0) {
  var rgb = {
      "ReconScanning": "170,255,255",
      "AttemptLogin": "111,217,46",
      "AbusiveSpam": "102,51,14",
      "AnomalyTraffic": "119,136,153",
      "AttemptExploit": "218,112,214",
      "AvailabilityDDoS": "169,0,0",
      "AvailabilityDoS": "229,46,46",
      "IntrusionBotnet": "255,140,0",
      "IntrusionUserCompromise": "204,42,20",
      "VulnerableConfig": "255,228,181",
      "VulnerableOpen": "238,232,170",
  }[cat] || "170,170,170";
  return "rgba(" + rgb + "," + alpha + ")";
}

// Create graph with numbers of events per day
function create_event_graph(elem, event_data) { 
  const N_DAYS = 30;
  // Get list of dates from today to N days
  // We use this both to get data from "ipinfo.events" and as labels in the graph, since the same format is OK for both
  let dates = [];
  let i;
  for (i = N_DAYS; i >= 0; i--) {
     dates.push(moment().subtract(i, "days").format("YYYY-MM-DD"));
  }
  // Construct datasets, one for each category, values are numbers of events per day
  let datasets = [];
  for (evtrec of event_data) {
    date_ix = dates.indexOf(evtrec.date);
    if (date_ix == -1)
      continue // Skip records with date out of range
    let ds = datasets.find(s => s.label == evtrec.cat); // Find dataset for the category
    if (ds === undefined) {
      // If not found, initialize a new dataset object
      ds = {
          label: evtrec.cat,
          data: new Array(dates.length).fill(0),
          backgroundColor: category2color(evtrec.cat, 0.5),
          borderWidth: 1,
      }
      datasets.push(ds);
    }
    ds.data[date_ix] += evtrec.n;
  }
  // Create the plot
  let event_chart = new Chart('plot-events', {
      type: 'bar',
      data: {
          labels: dates.map(d => moment(d).format("MMM D")),
          datasets: datasets
      },
      options: {
          animation: false,
          responsive: true,
          maintainAspectRatio: false,
          scales: {
              xAxes: [{
                  stacked: true
              }],
              yAxes: [{
                  min: 0,
                  stacked: true,
                  scaleLabel: {
                      display: true,
                      labelString: "Number of events",
                  },
                  ticks: {
                      precision: 0,
                      beginAtZero:true,
                  }
              }]
          },
          legend: {
            position: 'bottom'
          },
          tooltips: {
            mode: 'index'
          }
      }
  });
}


// Create graph with numbers of events per day
function create_pref_graph(elem, event_data) { 
    
    let ips = [];
    let i;
    for (evtrec of event_data) {
        evtrec_list = evtrec.split("\t")
        ip = evtrec_list[0]
        value = evtrec_list[1]
        ips.push(ip);
    }
    // Construct datasets, one for each category, values are numbers of events per day
    // let datasets = [];
    
    ds = new Array(ips.length).fill(0)

    
    for (evtrec of event_data) {

        
        evtrec_list = evtrec.split("\t")
        ip = evtrec_list[0]
        value = evtrec_list[1]



        ip_ix = ips.indexOf(ip);
        if (ip_ix == -1)
          continue // Skip records with date out of range

        
        ds[ip_ix] += value;
        // datasets.push(ds);

    }
    
    // Create the plot
    let event_chart = new Chart('plot-ips', {
        type: 'bar',
        label: ips,
        data: {
            labels: ips,
            datasets: [{
                label: '# of rep',
                data: ds,
                backgroundColor: category2color("ReconScanning", 0.5),
                borderWidth: 1
            }]
        },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                xAxes: [{
                    stacked: false
                }],
                yAxes: [{
                    min: 0,
                    stacked: false,
                    scaleLabel: {
                        display: true,
                        labelString: "Number of events",
                    },
                    ticks: {
                        precision: 0,
                        beginAtZero:true,
                    }
                }]
            },
            legend: {
              position: 'bottom'
            },
            tooltips: {
              mode: 'index'
            }
        }
    });
  }

  // Create graph with numbers of events per day
function create_dshield_graph(elem, event_data) { 
    
    const N_DAYS = 30;
    // Get list of dates from today to N days
    // We use this both to get data from "ipinfo.events" and as labels in the graph, since the same format is OK for both
    let dates = [];
    let i;
    for (i = N_DAYS; i >= 0; i--) {
       dates.push(moment().subtract(i, "days").format("YYYY-MM-DD"));
    }
    // Construct datasets, one for each category, values are numbers of events per day
    let datasets = new Array(dates.length).fill(0);
    for (evtrec of event_data) {
      date_ix = dates.indexOf(evtrec.date);
      if (date_ix == -1)
        continue // Skip records with date out of range


    datasets[date_ix] += evtrec.targets;
    }

    // Create the plot
    let event_chart = new Chart('plot-dshield', {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [{
                label: '# of reports',
                data: datasets,
                backgroundColor: category2color("ReconScanning", 0.5),
                borderWidth: 1
            }]
        },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                xAxes: [{
                    stacked: true
                }],
                yAxes: [{
                    min: 0,
                    stacked: true,
                    scaleLabel: {
                        display: true,
                        labelString: "Number of events",
                    },
                    ticks: {
                        precision: 0,
                        beginAtZero:true,
                    }
                }]
            },
            legend: {
              position: 'bottom'
            },
            tooltips: {
              mode: 'index'
            }
        }
    });
  }
  var rgb = new Array();
  function bl_category2color(cat, alpha=1.0) {
    if(rgb[cat] === undefined){
        color = Math.round(Math.random()*255) + "," + Math.round(Math.random()*255) + "," + Math.round(Math.random()*255);
        rgb[cat] = color
    }
    // var rgb = {
    //     "ReconScanning": "170,255,255",
    //     "AttemptLogin": "111,217,46",
    //     "AbusiveSpam": "102,51,14",
    //     "AnomalyTraffic": "119,136,153",
    //     "AttemptExploit": "218,112,214",
    //     "AvailabilityDDoS": "169,0,0",
    //     "AvailabilityDoS": "229,46,46",
    //     "IntrusionBotnet": "255,140,0",
    //     "IntrusionUserCompromise": "204,42,20",
    //     "VulnerableConfig": "255,228,181",
    //     "VulnerableOpen": "238,232,170",
    // }[cat] || "170,170,170";
    color = "rgba(" + rgb[cat] + "," + alpha + ")"
    return color;
  }
 // Create graph with numbers of events per day
 function create_bl_graph(elem, event_data) { 
    var format = function(time, format){
        var t = new Date(time);
        var tf = function(i){return (i < 10 ? '0' : '') + i};
        return format.replace(/yyyy|MM|dd|HH|mm|ss/g, function(a){
            switch(a){
                case 'yyyy':
                    return tf(t.getFullYear());
                    break;
                case 'MM':
                    return tf(t.getMonth() + 1);
                    break;
                case 'mm':
                    return tf(t.getMinutes());
                    break;
                case 'dd':
                    return tf(t.getDate());
                    break;
                case 'HH':
                    return tf(t.getHours());
                    break;
                case 'ss':
                    return tf(t.getSeconds());
                    break;
            }
        })
    }

    const N_DAYS = 30;
  // Get list of dates from today to N days
  // We use this both to get data from "ipinfo.events" and as labels in the graph, since the same format is OK for both
  let dates = [];
  let i;
  for (i = N_DAYS; i >= 0; i--) {
     dates.push(moment().subtract(i, "days").format("YYYY-MM-DD"));
  }
  // Construct datasets, one for each category, values are numbers of events per day
  let datasets = [];
  for (bl of event_data){
    //   
    for (evtrec of bl.h) {
        time = new Date(evtrec);
        date = format(time, 'yyyy-MM-dd');   //timeC界面显示格式
        date_ix = dates.indexOf(date);
        if (date_ix == -1)
          continue // Skip records with date out of range
        let ds = datasets.find(s => s.label == bl.n); // Find dataset for the category
        if (ds === undefined) {
          // If not found, initialize a new dataset object
          ds = {
              label: bl.n,
              data: new Array(dates.length).fill(0),

              backgroundColor: bl_category2color(bl.n, 0.5),

              borderWidth: 1,
          }
          datasets.push(ds);
          
        }
        if (ds.data[date_ix] === 0){
            ds.data[date_ix] += 1;
        }
        
        
      }
  }

  // Create the plot
  let event_chart = new Chart('plot-bl', {
      type: 'bar',
      data: {
        //   labels: dates.map(d => moment(d).format("MMM D")),
          labels: dates,
          datasets: datasets
      },
      options: {
          animation: false,
          responsive: true,
          maintainAspectRatio: false,
          scales: {
              xAxes: [{
                  stacked: true
              }],
              yAxes: [{
                  min: 0,
                  stacked: true,
                  scaleLabel: {
                      display: true,
                      labelString: "Number of events",
                  },
                  ticks: {
                      precision: 0,
                      beginAtZero:true,
                  }
              }]
          },
          legend: {
            position: 'bottom'
          },
          tooltips: {
            mode: 'index'
          }
      }
  });
  }
  
  function create_rep_graph(elem, event_data) { 
    
    const N_DAYS = 30;
    // Get list of dates from today to N days
    // We use this both to get data from "ipinfo.events" and as labels in the graph, since the same format is OK for both
    let dates = [];
    let i;
    for (i = N_DAYS; i >= 0; i--) {
       dates.push(moment().subtract(i, "days").format("YYYY-MM-DD"));
    }
    debugger
    // Construct datasets, one for each category, values are numbers of events per day
    let datasets = new Array(dates.length).fill(0);
    for (evtrec of event_data) {
      date_ix = dates.indexOf(evtrec.date);
      if (date_ix == -1)
        continue // Skip records with date out of range


    datasets[date_ix] += evtrec.reputation;
    }

    // Create the plot
    let event_chart = new Chart(elem, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [{
                label: '# of rep',
                data: datasets,
                backgroundColor: category2color("ReconScanning", 0.5),
                borderWidth: 1
            }]
        },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                xAxes: [{
                    stacked: true
                }],
                yAxes: [{
                    min: 0,
                    stacked: true,
                    scaleLabel: {
                        display: true,
                        labelString: "Number of events",
                    },
                    ticks: {
                        precision: 0,
                        beginAtZero:true,
                    }
                }]
            },
            legend: {
              position: 'bottom'
            },
            tooltips: {
              mode: 'index'
            }
        }
    });
  }