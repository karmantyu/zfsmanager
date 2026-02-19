#!/usr/bin/env perl

require './zfsmanager-lib.pl';
ReadParse();
use Data::Dumper;
my $can_pool_props = has_acl_permission('upool_properties');

if (!is_valid_pool_name($in{'pool'})) { error($text{'error_invalid_pool'} || "Invalid pool name"); }
if (!is_valid_dev_index($in{'dev'})) { error("Invalid device index"); }

ui_print_header(undef, $text{'vdev_title'}, "", undef, 1, 1);

my %status = zpool_status($in{'pool'});
if (!defined $status{$in{'dev'}}{name}) { error("Unknown device index"); }
my (undef, undef, undef, undef, $label) = get_disk_details($status{$in{'dev'}}{name});
$label = '-' if (!defined($label) || $label eq '');

print ui_columns_start([ "Virtual Device", "Label", "State", "Read", "Write", "Cksum" ]);
print ui_columns_row([h($status{$in{'dev'}}{name}), h($label), h($status{$in{'dev'}}{state}), h($status{$in{'dev'}}{read}), h($status{$in{'dev'}}{write}), h($status{$in{'dev'}}{cksum})]);
print ui_columns_end();

$parent = $status{$in{'dev'}}{parent};
if ($status{$in{'dev'}}{parent} =~ 'pool') 
{
} else {
	print ui_columns_start([ "Parent", "State", "Read", "Write", "Cksum" ]);
	print ui_columns_row(["<a href='config-vdev.cgi?pool=".u($in{'pool'})."&dev=".$status{$in{'dev'}}{parent}."'>".h($status{$parent}{name})."</a>", h($status{$parent}{state}), h($status{$parent}{read}), h($status{$parent}{write}), h($status{$parent}{cksum})]);
	print ui_columns_end();
}
ui_zpool_list($in{'pool'});
if (($status{$in{'dev'}}{name} =~ "cache") || ($status{$in{'dev'}}{name} =~ "logs") || ($status{$in{'dev'}}{name} =~ "spare") || ($status{$in{'dev'}}{name} =~ /mirror/) || ($status{$in{'dev'}}{name} =~ /raidz/))
{
print "Children: ";
	foreach $key (sort(keys %status))
	{
		if (defined $status{$key}{parent} && $status{$key}{parent} eq $in{'dev'}) 
		{
			print "<a href='config-vdev.cgi?pool=".u($in{pool})."&dev=$key'>".h($status{$key}{name})."</a>  ";
		}
	}
} elsif (($config{'pool_properties'} =~ /1/) && $can_pool_props) {
	print ui_table_start("Tasks", "width=100%", "10", ['align=left'] );
	if ($status{$in{'dev'}}{state} =~ "ONLINE")	{
		print ui_table_row("Offline: ", ui_post_action_link('Bring device offline', 'cmd.cgi',
			{ 'cmd' => 'vdev', 'action' => 'offline', 'pool' => $in{'pool'}, 'vdev' => $status{$in{'dev'}}{name}, 'xnavigation' => 1 })."<br />");
	}
	else { #elsif ($status{$in{'dev'}}{state} =~ "OFFLINE") {
		print ui_table_row("Online: ", ui_post_action_link('Bring device online', 'cmd.cgi',
			{ 'cmd' => 'vdev', 'action' => 'online', 'pool' => $in{'pool'}, 'vdev' => $status{$in{'dev'}}{name}, 'xnavigation' => 1 })."<br />");
	}
	print ui_table_row("Replace: ", ui_post_action_link('Replace device', 'cmd.cgi',
		{ 'cmd' => 'replace', 'vdev' => $status{$in{'dev'}}{name}, 'pool' => $in{'pool'}, 'xnavigation' => 1 })."<br />");
	print ui_table_row("Remove: ", ui_post_action_link('Remove device', 'cmd.cgi',
		{ 'cmd' => 'vdev', 'action' => 'remove', 'pool' => $in{'pool'}, 'vdev' => $status{$in{'dev'}}{name}, 'xnavigation' => 1 },
		"Are you sure you want to remove device ".$status{$in{'dev'}}{name}."?")."<br />");
	print ui_table_row("Detach: ", ui_post_action_link('Detach device', 'cmd.cgi',
		{ 'cmd' => 'vdev', 'action' => 'detach', 'pool' => $in{'pool'}, 'vdev' => $status{$in{'dev'}}{name}, 'xnavigation' => 1 },
		"Are you sure you want to detach device ".$status{$in{'dev'}}{name}."?")."<br />");
	print ui_table_row("Clear: ", ui_post_action_link('Clear errors', 'cmd.cgi',
		{ 'cmd' => 'vdev', 'action' => 'clear', 'pool' => $in{'pool'}, 'vdev' => $status{$in{'dev'}}{name}, 'xnavigation' => 1 })."<br />");
	print ui_table_end();
}

ui_print_footer("status.cgi?pool=".u($in{'pool'}), h($in{'pool'}));
