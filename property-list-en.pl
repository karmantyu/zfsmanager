BEGIN { push(@INC, ".."); };
use WebminCore;
init_config();

sub property_desc
#deprecated, migrate all to lang/en
{
my %hash = ();
return %hash;
}


