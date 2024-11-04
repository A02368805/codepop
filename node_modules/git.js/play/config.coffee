git = require './index'

print = (p) ->
	p.then (val) ->
		console.log val
	.fail (err) ->
		console.error err

print git.config.user.name
print git.config.user.email
print git.config.global.user.name
print git.config.global.user.email
print git.config.system.user.name
print git.config.system.user.email
