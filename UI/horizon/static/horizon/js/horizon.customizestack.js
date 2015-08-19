/**
 *
 * HeatTop JS Framework
 * Dependencies: jQuery 1.7.1 or later, d3 v3 or later
 * Date: June 2013
 * Description: JS Framework that subclasses the D3 Force Directed Graph library to create
 * Heat-specific objects and relationships with the purpose of displaying
 * Stacks, Resources, and related Properties in a Resource Topology Graph.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

var cs_container = "#heat_topology";

function cs_get_canvas_data() {
  var resources = [];
  $.each(nodes, function(i, node) {
    resources.push(node.details);
  });
  return(JSON.stringify(resources));
}

function del_items(name) {
  var id; 
  id = 'id_' + name;
  $('#'+id+' option:selected').remove();
}

function edit_item(name, add_link) {
  var id, widget, btn_grp, edit_btn, edit_link, value = null, index; 
  id = 'id_' + name;
  widget = $('#'+id);
  btn_grp = widget.next();
  edit_btn = $(btn_grp.children()[2]);
  edit_link = add_link.replace('add_item', 'edit_item');
  $.each(widget.children(), function(i, option) {
    if($(option).is(':selected')) {
      value = $(option).attr('value');
      index = i;
    }
  });
  if(value) {
    edit_btn.addClass('ajax-add ajax-modal');
    edit_btn.attr('href', edit_link + value + '/');
    edit_btn.attr('option-to-edit', index);
  } else {
    edit_btn.removeClass('ajax-add ajax-modal');
    edit_btn.attr('href', 'javascript:void(0);');
  }
}

function cs_update(){
  node = node.data(nodes, function(d) { return d.name; });
  link = link.data(links);

  var nodeEnter = node.enter().append("g")
    .attr("class", "node")
    .attr("node_name", function(d) { return d.name; })
    .attr("node_id", function(d) { return d.instance; })
    .call(force.drag);

  nodeEnter.append("image")
    .attr("xlink:href", function(d) { return d.image; })
    .attr("id", function(d){ return "image_"+ d.name; })
    .attr("x", function(d) { return d.image_x; })
    .attr("y", function(d) { return d.image_y; })
    .attr("width", function(d) { return d.image_size; })
    .attr("height", function(d) { return d.image_size; });
  node.exit().remove();

  link.enter().insert("svg:line", "g.node")
    .attr("class", "link")
    .style("stroke-width", function(d) { return Math.sqrt(d.value); });
  link.exit().remove();
  //Setup click action for all nodes
  node.on("mouseover", function(d) {
    var icon;
    if(!node_selected) {
      icon = $('<img/>');
      icon.attr('src', d.image);
      $("#node_icon").html(icon);
      showBrief(d.details);
      $("#node_info").html(d.info_box);
    }
  });
  node.on("mouseout", function() {
    if(!node_selected) {
      $("#node_icon").html('');
      $("#node_info").html('');
    }
  });
  node.on("click", function(d) {
    $('#detail_box').perfectScrollbar('destroy');
    icon = $('<img/>');
    icon.attr('src', d.image);
    $('#node_icon').html(icon);
    showDetails(d.details);
    $('#opt_bar').show();
    $('#cus_stack_action_delete').attr('href',"/project/customize_stack/delete_resource/" + d.name + "/");
    $('#cus_stack_action_edit').attr('href',"/project/customize_stack/edit_resource/" + d.name + "/");
    $('#detail_box').perfectScrollbar();
    node_selected = true;
    d3.event.stopPropagation()
  });

  force.start();
}

function showBrief(d) {
  var details = $('#node_info'),
    seg;
  details.html('');
  seg = $('<h3></h3>');
  seg.html(d.resource_name);
  details.append(seg);
  seg = $('<h4></h4>');
  seg.html('type');
  details.append(seg);
  seg = $('<p></p>');
  seg.html(d.resource_type);
  details.append(seg);
}

function showDetails(d) {
  var details = $('#node_info'),
    seg;

  showBrief(d);
  for(var key in d) {
    if(key == 'resource_name' || key == 'resource_type')
      continue;
    seg = $('<h4></h4>');
    seg.html(key);
    details.append(seg);
    seg = $('<p></p>');
    seg.html(d[key]?d[key]:'None');
    details.append(seg);
  }
}

function tick() {
  link.attr("x1", function(d) { return d.source.x; })
    .attr("y1", function(d) { return d.source.y; })
    .attr("x2", function(d) { return d.target.x; })
    .attr("y2", function(d) { return d.target.y; });

  node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
}

function findNode(name) {
  for (var i = 0; i < nodes.length; i++) {
    if (nodes[i].name === name){ return nodes[i]; }
  }
}

function findNodeIndex(name) {
  for (var i = 0; i < nodes.length; i++) {
    if (nodes[i].name === name){ return i; }
  }
}

function cs_addResource(resource) {
  var toAdd = $.parseJSON(resource);
  cs_addNode(toAdd);
  cs_build_links();
  cs_update();
}

function cs_addNode (node) {
  nodes.push(node);
  needs_update = true;
}

function removeNode (name) {
  var i = 0;
  var n = findNode(name);
  while (i < links.length) {
    if (links[i].source === n || links[i].target === n) {
      links.splice(i, 1);
    } else {
      i++;
    }
  }
  nodes.splice(findNodeIndex(name),1);
  needs_update = true;
}

function remove_nodes(old_nodes, new_nodes){
  //Check for removed nodes
  for (var i=0;i<old_nodes.length;i++) {
    var remove_node = true;
    for (var j=0;j<new_nodes.length;j++) {
      if (old_nodes[i].name === new_nodes[j].name){
        remove_node = false;
        break;
      }
    }
    if (remove_node === true){
      removeNode(old_nodes[i].name);
    }
  }
}

function cs_build_links(){
  for (var i=0;i<nodes.length;i++){
    build_node_links(nodes[i]);
    build_reverse_links(nodes[i]);
  }
}

function build_node_links(node){
  for (var j=0;j<node.required_by.length;j++){
    var push_link = true;
    var target_idx = '';
    var source_idx = findNodeIndex(node.name);
    //make sure target node exists
    try {
      target_idx = findNodeIndex(node.required_by[j]);
    } catch(err) {
      push_link =false;
    }
    //check for duplicates
    for (var lidx=0;lidx<links.length;lidx++) {
      if (links[lidx].source === source_idx && links[lidx].target === target_idx) {
        push_link=false;
        break;
      }
    }

    if (push_link === true && (source_idx && target_idx)){
      links.push({
        'source':source_idx,
        'target':target_idx,
        'value':1
      });
    }
  }
}

function build_reverse_links(node){
  for (var i=0;i<nodes.length;i++){
    if(nodes[i].required_by){
      for (var j=0;j<nodes[i].required_by.length;j++){
        var dependency = nodes[i].required_by[j];
        //if new node is required by existing node, push new link
        if(node.name === dependency){
          links.push({
            'source':findNodeIndex(nodes[i].name),
            'target':findNodeIndex(node.name),
            'value':1
          });
        }
      }
    }
  }
}

function zoomed() {
    if (d3.event.sourceEvent.type == 'wheel' || d3.event.sourceEvent.type == 'dblclick') {
        group.transition().duration(300).attr("transform",
            "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
    } else {
        group.attr("transform",
            "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
    }
} 

if ($(cs_container).length){
  var width = $(cs_container).width(),
    height = window.innerHeight - 230;
    if (height < 500){
      height = 500;
    }
    ajax_url,
    graph,
    template_name = $(cs_container).attr('name');
  $('#opt_bar').hide();
  if (template_name) {
    ajax_url = '/project/customize_stack/get_template_data/' + template_name + '/';
    $.ajax({
      url: ajax_url,  
      type: 'GET',  
      dataType: 'json',  
      async: false,  
      success: function(json) {
        graph = json;
      }
    });
  } else {
    graph = {
      'nodes': []
    }
  }
  var force = d3.layout.force()
      .nodes(graph.nodes)
      .links([])
      .gravity(0.1)
      .charge(-2000)
      .linkDistance(100)
      .size([width, height])
      .on("tick", tick),
    zoom = d3.behavior.zoom()
      .scaleExtent([0.1, 10])
      .on("zoom", zoomed),
    svg = d3.select(cs_container).append("svg")
      .attr("width", width)
      .attr("height", height)
      .call(zoom),
    group = svg.append("g"),
    node = group.selectAll(".node"),
    link = group.selectAll(".link"),
    needs_update = false,
    nodes = force.nodes(),
    links = force.links(),
    node_selected = false;
    
  svg.on("click", function() {
    node_selected = false;
    $("#node_icon").html('');
    $("#node_info").html('');
    $('#opt_bar').hide();
    $('#detail_box').perfectScrollbar('destroy');
  });

  cs_build_links();
  cs_update();
  
  //resize the canvas when the window is resized.
  $(window).resize(function(){
    var width = $(cs_container).width(),
    height = window.innerHeight - 230;
    if (height < 500){
      height = 500;
    }
    force.size([width, height]);
    svg.attr("width", width);
    svg.attr("height", height);
    force.resume();
    $('#detail_box').perfectScrollbar('update');
  });
}
