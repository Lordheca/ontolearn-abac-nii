package policy

# Authorization policy for the OntoLearn Annotator.
#
# Input contract (built by inheritance_service/main/libs/access_lib/access_decision_lib.py
# from the annotator's request in ontolearn-annotator/src/lib/abac-client.ts):
#
#   {
#     "subject":      {"id": <userId>, "role": "ADMIN" | "USER", "email": <string>},
#     "resource":     {"id": <projectId>, "type": <resource type, see below>},
#     "action":       {"name": "read" | "write" | "delete" | "list" | "invite" | "edit"},
#     "environments": {<env function name>: [<values>]}
#   }
#
# `subject.role` is the caller's Role in THIS project, read from the annotator's
# ProjectMember table (Prisma enum Role: ADMIN | USER). The annotator already denies
# non-members before calling here, so a request reaching this policy always comes from
# a member of resource.id — this policy decides what that member may do, not whether
# they belong.
#
# Resource types and actions in use (ontolearn-annotator/src/lib/abac-action-categories.ts):
#   settings    read, write
#   data        read, write, delete
#   task        read, write
#   playground  read, write
#   project     read, write, delete
#   statistics  read
#   user        list, invite, delete, edit
#   sourceType  list

# Deny by default: an unknown role, resource type or action is refused.
default allow := false

# A project ADMIN has full control over that project.
allow if {
	input.subject.role == "ADMIN"
}

# A USER may read and list everything in a project they belong to.
allow if {
	input.subject.role == "USER"
	input.action.name in {"read", "list"}
}

# A USER may also do the annotation work itself: complete tasks and use the playground.
allow if {
	input.subject.role == "USER"
	input.resource.type in {"task", "playground"}
	input.action.name == "write"
}
