fs = require 'fs'
path = require 'path'
exeq = require 'exequte'
_ = require 'underscore'

# load command plugins
plugins = fs.readdirSync(path.join(__dirname, 'commands'))
	.filter (file) ->
		name = path.basename(file, '.coffee')
		switch name
			when 'git' then false
			else true
	.map (file) ->
		name = path.basename(file, '.coffee')
		factory = require "./commands/#{name}"
		factory.cmdname = name
		return factory

# executes given git command
exec = (cwd, cmd, args, opts) ->
	args = [] unless args
	argv = [cmd, args...]
	exeq 'git', argv, {cwd: cwd, verbose: opts.verbose}

# creates git command runner
git = (dir, opts) ->
	unless arguments.length
		dir = process.cwd()
		opts = {}

	if _.isObject dir
		opts = dir
		dir = opts.dir

	dir = process.cwd() unless dir

	unless fs.existsSync dir
		throw new Error "#{dir} does not exist"

	opts = {} unless opts

	# runs given command
	run = (cmd, args) ->
		exec dir, cmd, args, opts

	api = {run: run}

	# inject commands
	plugins.forEach (factory) ->
		cmdfn = factory api
		api[factory.cmdname] = cmdfn
		(cmdfn.aliases || []).forEach (name) ->
			api[name] = cmdfn

	return api

module.exports = git
