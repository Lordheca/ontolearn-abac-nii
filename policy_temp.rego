package policy

# By default, deny access
default allow = false

# Allow access if all conditions in this rule are met
allow if {
    attributes_within_limits
    action_is_valid
    domain_matches
}

# Allow access if the name matches the domain
allow if {
    name_matches
    domain_matches
}

# Allow access if the subscription matches the domain
allow if {
    subscription_matches
    domain_matches
}

# Allow access if the action is to add an entity and the domain matches
allow if {
    action_is_addEntity
    domain_matches
}

# Allow access if the action is to remove an entity and the domain matches
allow if {
    action_is_rmEntity
    domain_matches
}

# Allow access if the action is to add an attribute and the domain matches
allow if {
    action_is_addAttr
    domain_matches
}

# Allow access if the action is to remove an attribute and the domain matches
allow if {
    action_is_rmAttr
    domain_matches
}

# Check if the object's attributes fall within the limits specified by the subject's attributes
attributes_within_limits if {
    # Ensure that the Max_atom attribute of the object is less than or equal to that of the subject
    input.obj.attr[_].Max_atom <= input.subj.attr[_].Max_atom
    # Ensure that the max_action attribute of the object is less than or equal to that of the subject
    input.obj.attr[_].max_action <= input.subj.attr[_].max_action
    # Ensure that the target_sim attribute of the object is less than or equal to that of the subject
    input.obj.attr[_].target_sim <= input.subj.attr[_].target_sim
    # Ensure that the max_len attribute of the object is less than or equal to that of the subject
    input.obj.attr[_].max_len <= input.subj.attr[_].max_len
    # Ensure that the n_episodes attribute of the object is less than or equal to that of the subject
    input.obj.attr[_].n_episodes <= input.subj.attr[_].n_episodes
}

# Check if the action specified is valid; in this case, "Fusion" is the only valid action
action_is_valid if {
    input.action.attr[_] == "Fusion"
}

# Check if the domain attribute of the object matches the domain attribute of the subject
domain_matches if {
    some i, j
    input.obj.attr[i].domain == input.subj.attr[j].domain
}


# Check if the name attribute of the subject matches the name attribute of the object
name_matches if {
    input.subj.attr[_].name == input.obj.attr[_].name
}

# Check if the subscription attribute of the subject matches the subscription attribute of the object
subscription_matches if {
    input.subj.attr[_].subscription == input.obj.attr[_].subscription
}

# Check if the action is to add an entity
action_is_addEntity if {
    input.action.attr[_].addEntity != null
}

# Check if the action is to remove an entity
action_is_rmEntity if {
    input.action.attr[_].rmEntity != null
}

# Check if the action is to add an attribute
action_is_addAttr if {
    input.action.attr[_].addAttr != null
}

# Check if the action is to remove an attribute
action_is_rmAttr if {
    input.action.attr[_].rmAttr != null
}
