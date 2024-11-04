_ = require 'underscore'

# config command plugin
module.exports = (git) ->
	# todo support more options
	config = (opts) ->
		name = opts.name
		value = opts.value
		args = if value then [name, value] else ['--get', name]
		git.run('config', args)
	local = create git
	config.system = create git, ['--system']
	config.global = create git, ['--global']
	config.get = local.get
	config.set = local.set
	config.user = local.user
	config

# creates config api
create = (git, opts) ->
	opts = [] unless opts
	api =
		get: (name) ->
			git.run 'config', [opts..., name]
		set: (name, value) ->
			git.run 'config', [opts..., name, value]
	# user config
	user =
		name:
			get: -> api.get 'user.name'
			set: (value) -> api.set 'user.name', value
		email:
			get: -> api.get 'user.email'
			set: (value) -> api.set 'user.email', value
	api.user = createObj user
	api

createObj = (props) ->
	obj = {}
	Object.keys(props).forEach (key) ->
		val = props[key]
		if val.get? or val.set?
			Object.defineProperty(obj, key, val)
		else
			obj[key] = val
	obj
